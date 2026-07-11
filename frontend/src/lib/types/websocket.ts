import type { Participant } from './participant';
import type { QuestionIn } from './question';
import type { ResponseOut } from './response';

/** WebSocket close codes used by the application. */
export enum CloseCode {
    /** The host is already connected to another session. */
    HOST_ALREADY_CONNECTED = 1008,
    /** Invalid access token provided. */
    INVALID_TOKEN = 1008,
    /** The participant is already connected to another session */
    PARTICIPANT_RECONNECTED_ELSEWHERE = 1008,
}

/** Types of messages that can be sent in the meeting system. */
export enum MessageTypes {
    // meeting state
    MEETING_STATE = 'meeting_state',
    MEETING_STARTED = 'meeting_started',
    MEETING_ENDED = 'meeting_ended',
    NEXT_QUESTION = 'next_question',
    CURRENT_QUESTION = 'current_question',
    RESPONSE_RECEIVED = 'response_received',
    REVEAL = 'reveal',
    HOST_DISCONNECTED = 'host_disconnected',
    HOST_RECONNECTED = 'host_reconnected',
    PARTICIPANT_CONNECTED = 'participant_connected',
    PARTICIPANT_DISCONNECTED = 'participant_disconnected',
    PARTICIPANT_STATE = 'participant_state',
}

/** Payload for when a participant connects. */
export interface ParticipantConnectedPayload {
    /** The username of the joining participant */
    username: string;
}

/** Payload for when a participant disconnects */
export interface ParticipantDisconnectedPayload {
    /** The id of the disconnecting participant */
    id: string;
}

/** Payload for the current snapshot of the meeting state */
export interface MeetingStatePayload {
    /** The current question being discussed or None if the meeting has not started. */
    question: QuestionIn | null;
    /** List of responses received for the current question so far. */
    responses: ResponseOut[];
    /** List of participants in the meeting */
    participants: Participant[];
}

/** Payload for when a meeting has started */
export interface MeetingStartedPayload {
    /** The current question associated with the meeting start */
    question: QuestionIn;
}

/** Payload for when moving to the next question */
export interface NextQuestionPayload {
    /** The next question to be presented */
    question: QuestionIn;
}

/** Payload for managing the current question */
export interface CurrentQuestionPayload {
    /** The current question used in the meeting */
    question: QuestionIn;
}

/** Payload for receiving a participant's response to a question. */
export interface ResponseReceivedPayload {
    /** The participants response to the current question */
    response: ResponseOut;
}

/** Payload for revealing the current responses to participants */
export interface RevealMeetingPayload {
    /** All current responses to the active meeting question */
    responses: ResponseOut[];
}

// NOTE: Add other interfaces in here as needed

/** Maps each MessageType to its corresponding payload shape. */
interface PayloadMap {
    [MessageTypes.MEETING_STATE]: MeetingStatePayload;
    [MessageTypes.MEETING_STARTED]: MeetingStartedPayload;
    [MessageTypes.NEXT_QUESTION]: NextQuestionPayload;
    [MessageTypes.CURRENT_QUESTION]: CurrentQuestionPayload;
    [MessageTypes.RESPONSE_RECEIVED]: ResponseReceivedPayload;
    [MessageTypes.REVEAL]: RevealMeetingPayload;
    [MessageTypes.PARTICIPANT_CONNECTED]: ParticipantConnectedPayload;
    [MessageTypes.PARTICIPANT_DISCONNECTED]: ParticipantDisconnectedPayload;
    [MessageTypes.PARTICIPANT_STATE]: Participant;
    [MessageTypes.HOST_DISCONNECTED]: undefined;
    [MessageTypes.HOST_RECONNECTED]: undefined;
    [MessageTypes.MEETING_ENDED]: undefined;
}

// NOTE: Map extra MessageTypes to their corresponding payload shape in here

/** Resolves the payload type for a given MessageType, falling back to Record<string, any>. */
type WebInPayload<T extends MessageTypes> = T extends keyof PayloadMap
    ? PayloadMap[T]
    : Record<string, any>;

/**
 * A generic incoming WebSocket message where the payload type
 * is determined by the 'type' field.
 */
type WebInMessage<T extends MessageTypes> = { type: T; payload: WebInPayload<T> };

/** Union of all possible incoming WebSocket messages. */
export type WebIn =
    | WebInMessage<MessageTypes.MEETING_STATE>
    | WebInMessage<MessageTypes.MEETING_STARTED>
    | WebInMessage<MessageTypes.NEXT_QUESTION>
    | WebInMessage<MessageTypes.PARTICIPANT_CONNECTED>
    | WebInMessage<MessageTypes.PARTICIPANT_DISCONNECTED>
    | WebInMessage<MessageTypes.PARTICIPANT_STATE>
    | WebInMessage<MessageTypes.CURRENT_QUESTION>
    | WebInMessage<MessageTypes.RESPONSE_RECEIVED>
    | WebInMessage<MessageTypes.REVEAL>
    | WebInMessage<MessageTypes.MEETING_ENDED>
    | WebInMessage<MessageTypes.HOST_DISCONNECTED>
    | WebInMessage<MessageTypes.HOST_RECONNECTED>;
