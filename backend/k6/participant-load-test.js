// Craftmeet — k6 Participant WebSocket Load Test
// Measures WebSocket connection capacity, message-exchange latency, and
// response-submission throughput under concurrent participant load.
//
// Pre-requisite: run `python k6/setup.py` first to generate test-data.json
//
// The test expects a host to be driving the meeting.  Use the companion
// host-driver.py script in a separate terminal:
//
//   Terminal 1:  python k6/host-driver.py
//   Terminal 2:  k6 run k6/participant-load-test.js
//
// Or run a quick connection-only test without a host (connections will fail
// because the LiveRoom doesn't exist — useful for raw connect-capacity tests).
//
// Usage:
//   k6 run --vus 20 --duration 30s k6/participant-load-test.js
//   k6 run k6/participant-load-test.js

import ws from "k6/ws";
import { sleep } from "k6";
import { Trend, Rate, Counter } from "k6/metrics";

// custom metrics
const connectDuration = new Trend("ws_connect_duration_ms", true);
const timeToState = new Trend("ws_time_to_state_ms", true);
const timeToQuestion = new Trend("ws_time_to_question_ms", true);
const connectErrorRate = new Rate("ws_connect_errors");
const messagesReceived = new Counter("ws_messages_received");
const responsesSent = new Counter("ws_responses_sent");

// k6's open() resolves relative to the working directory (backend/).
// The file lives at backend/k6/test-data.json.
let testData;
try {
  testData = JSON.parse(open("./k6/test-data.json"));
} catch (_) {
  // Fallback if running from the k6/ directory itself
  testData = JSON.parse(open("./test-data.json"));
}

const WS_BASE = testData.base_url
  .replace("http://", "ws://")
  .replace("https://", "wss://")
  .replace("/api/v1", "");

const MEETING_ID = testData.meeting_id;
const QUESTIONS = testData.questions || [];
const PARTICIPANTS = testData.participants;

if (!PARTICIPANTS || PARTICIPANTS.length === 0) {
  throw new Error("No participants in test-data.json. Run setup.py first.");
}

// k6 options
// Default ramp: 0 → 50 over 20s, hold 50 for 60s, ramp down 50 → 0 over 20s.
// Override --vus and --duration on the CLI to change peak concurrency.
//
// IMPORTANT: regenerate test-data.json with at least as many participants
// as your peak VU count so each VU gets a unique participant:
//   python k6/setup.py --participants 500
//
export const options = {
  stages: [
    { duration: "20s", target: 500 }, // ramp up
    { duration: "60s", target: 500 }, // hold at peak
    { duration: "20s", target: 0 }, // ramp down
  ],

  thresholds: {
    ws_connect_duration_ms: ["p(95)<3000"],
    ws_connect_errors: ["rate<0.10"],
  },

  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

// helpers
function pickParticipant() {
  const idx = (__VU - 1) % PARTICIPANTS.length;
  return PARTICIPANTS[idx];
}

function buildWsUrl() {
  return `${WS_BASE}/api/v1/meetings/${MEETING_ID}/participant/ws`;
}

/**
 * Build a response for the given question type.
 * Returns null if we can't auto-respond to this question type.
 */
function buildResponse(question, participant) {
  const base = {
    question_id: question.id,
    participant_id: participant.id,
  };

  switch (question.type) {
    case "yes_no":
      return { ...base, type: "yes_no", value: Math.random() > 0.5 };
    case "rating_scale":
      return {
        ...base,
        type: "rating_scale",
        value: Math.floor(Math.random() * 5) + 1,
      };
    case "multiple_choice":
      return { ...base, type: "multiple_choice", selected_options: [1] };
    case "long_answer":
      return { ...base, type: "long_answer", content: "k6 auto-response" };
    case "ranked_voting":
      return { ...base, type: "ranked_voting", rank_1: 1, rank_2: 2 };
    default:
      return null;
  }
}

/**
 * Find question metadata by its ID.
 */
function findQuestion(questionId) {
  return QUESTIONS.find((q) => q.id === questionId) || null;
}

// VU function
export default function () {
  const participant = pickParticipant();
  const url = buildWsUrl();
  const cookieHeader = `${participant.cookie_name}=${participant.token}`;

  let connectStart = Date.now();
  let stateStart = 0;
  let questionStart = 0;
  let respondedTo = new Set(); // question IDs we've already answered

  const res = ws.connect(
    url,
    {
      headers: { Cookie: cookieHeader },
      tags: { vu: __VU, participant: participant.username },
    },
    function (socket) {
      // open
      socket.on("open", () => {
        connectDuration.add(Date.now() - connectStart);

        socket.send(
          JSON.stringify({
            type: "participant_connected",
            payload: { username: participant.username },
          }),
        );

        stateStart = Date.now();
      });

      // message
      socket.on("message", (raw) => {
        messagesReceived.add(1);

        let msg;
        try {
          msg = JSON.parse(raw);
        } catch (_) {
          return;
        }

        switch (msg.type) {
          case "participant_state":
            timeToState.add(Date.now() - stateStart);
            stateStart = 0;
            break;

          case "current_question":
          case "meeting_started": {
            // Extract the question from the payload
            const question =
              msg.type === "meeting_started"
                ? msg.payload?.question
                : msg.payload?.question;

            if (!question) break;

            if (msg.type === "meeting_started") {
              questionStart = Date.now();
            } else if (questionStart > 0) {
              timeToQuestion.add(Date.now() - questionStart);
              questionStart = 0;
            }

            // Don't respond twice to the same question
            if (respondedTo.has(question.id)) break;

            const qMeta = findQuestion(question.id) || question;
            const response = buildResponse(qMeta, participant);
            if (response) {
              socket.send(
                JSON.stringify({
                  type: "response_received",
                  payload: { response: response },
                }),
              );
              responsesSent.add(1);
              respondedTo.add(question.id);
            }
            break;
          }

          case "next_question": {
            // Reset for the new question
            questionStart = Date.now();
            const question = msg.payload?.question;
            if (!question) break;

            const qMeta = findQuestion(question.id) || question;
            const response = buildResponse(qMeta, participant);
            if (response && !respondedTo.has(question.id)) {
              socket.send(
                JSON.stringify({
                  type: "response_received",
                  payload: { response: response },
                }),
              );
              responsesSent.add(1);
              respondedTo.add(question.id);
            }
            break;
          }

          case "meeting_ended":
            socket.close();
            break;

          case "host_disconnected":
          case "host_reconnected":
          case "reveal":
            // Expected broadcast messages
            break;

          default:
            if (msg.type !== "__host_verify") {
              // ignore internal ping
            }
        }
      });

      // close
      socket.on("close", () => {
        // Normal teardown
      });

      // error
      socket.on("error", () => {
        connectErrorRate.add(1);
      });

      // safety timeout
      // Close after 30 s so VUs cycle and new connections are attempted.
      socket.setTimeout(function () {
        socket.close();
      }, 30000);
    },
  );

  if (!res) {
    connectErrorRate.add(1);
    return;
  }

  sleep(1);
}
