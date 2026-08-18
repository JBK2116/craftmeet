import type { Participant } from './participant';
import type { QuestionIn, QuestionOut } from './question';
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
    // add question feature
    ADD_QUESTION = 'add_question',
    ADD_QUESTION_SUCCESS = 'add_question_success',
    ADD_QUESTION_FAILED = 'add_question_failed',
    // meeting state
    MEETING_STATE = 'meeting_state',
    MEETING_STARTED = 'meeting_started',
    MEETING_ENDED = 'meeting_ended',
    // question state
    NEXT_QUESTION = 'next_question',
    CURRENT_QUESTION = 'current_question',
    // response handling
    RESPONSE_RECEIVED = 'response_received',
    REVEAL = 'reveal',
    // host connection
    HOST_DISCONNECTED = 'host_disconnected',
    HOST_RECONNECTED = 'host_reconnected',
    // participant connection
    PARTICIPANT_CONNECTED = 'participant_connected',
    PARTICIPANT_DISCONNECTED = 'participant_disconnected',
    PARTICIPANT_STATE = 'participant_state',
    PARTICIPANTS_STATE = 'participants_state',
    // chat state
    CHAT_RECEIVED = 'chat_received',
    CHAT_STATE = 'chat_state',
}

/** Payload for when requesting to add a new question to a live meeting */
export interface AddQuestionPayload {
    /** The question to add */
    question: QuestionOut;
}

/** Payload for when an add question request succeeds */
export interface AddQuestionSuccessPayload {
    /** The question to add */
    question: QuestionIn;
}

/** Payload for when an add question request fails */
export interface AddQuestionFailedPayload {
    /** The reason for the failure */
    detail: string;
}

/** Payload for when a participant disconnects */
export interface ParticipantDisconnectedPayload {
    /** The id of the disconnecting participant */
    id: string;
}

/** Payload for the current snapshot of the participants state */
export interface ParticipantsStatePayload {
    /** List of all participants registered in the meeting */
    participants: Participant[];
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

/** A chat message */
export interface ChatMessage {
    /** The name of the user who sent the message */
    name: string;
    /** The id of the user that sent the message */
    u_id: string;
    /** The content of the chat message */
    message: string;
    /** Whether the user is the host of the chat */
    is_host: boolean;
    /** The time of the message's creation */
    created_at: string;
}

/** Represents the state for chat bar. */
export interface ChatStatePayload {
    /** Array of chat messages. */
    chats: ChatMessage[];
}

/** Payload for when a chat message arrives. */
export interface ChatReceivedPayload {
    /** The incoming chat message */
    chat: ChatMessage;
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
    [MessageTypes.ADD_QUESTION]: AddQuestionPayload;
    [MessageTypes.ADD_QUESTION_SUCCESS]: AddQuestionSuccessPayload;
    [MessageTypes.ADD_QUESTION_FAILED]: AddQuestionFailedPayload;
    [MessageTypes.MEETING_STATE]: MeetingStatePayload;
    [MessageTypes.MEETING_STARTED]: MeetingStartedPayload;
    [MessageTypes.NEXT_QUESTION]: NextQuestionPayload;
    [MessageTypes.CURRENT_QUESTION]: CurrentQuestionPayload;
    [MessageTypes.RESPONSE_RECEIVED]: ResponseReceivedPayload;
    [MessageTypes.CHAT_RECEIVED]: ChatReceivedPayload;
    [MessageTypes.CHAT_STATE]: ChatStatePayload;
    [MessageTypes.REVEAL]: RevealMeetingPayload;
    [MessageTypes.PARTICIPANT_CONNECTED]: Participant;
    [MessageTypes.PARTICIPANT_DISCONNECTED]: ParticipantDisconnectedPayload;
    [MessageTypes.PARTICIPANT_STATE]: Participant;
    [MessageTypes.PARTICIPANTS_STATE]: ParticipantsStatePayload;
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
    | WebInMessage<MessageTypes.ADD_QUESTION_SUCCESS>
    | WebInMessage<MessageTypes.ADD_QUESTION_FAILED>
    | WebInMessage<MessageTypes.MEETING_STATE>
    | WebInMessage<MessageTypes.MEETING_STARTED>
    | WebInMessage<MessageTypes.NEXT_QUESTION>
    | WebInMessage<MessageTypes.PARTICIPANT_CONNECTED>
    | WebInMessage<MessageTypes.PARTICIPANT_DISCONNECTED>
    | WebInMessage<MessageTypes.PARTICIPANT_STATE>
    | WebInMessage<MessageTypes.PARTICIPANTS_STATE>
    | WebInMessage<MessageTypes.CURRENT_QUESTION>
    | WebInMessage<MessageTypes.RESPONSE_RECEIVED>
    | WebInMessage<MessageTypes.CHAT_RECEIVED>
    | WebInMessage<MessageTypes.CHAT_STATE>
    | WebInMessage<MessageTypes.REVEAL>
    | WebInMessage<MessageTypes.MEETING_ENDED>
    | WebInMessage<MessageTypes.HOST_DISCONNECTED>
    | WebInMessage<MessageTypes.HOST_RECONNECTED>;
