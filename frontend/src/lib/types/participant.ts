/** A Participant in a meeting. */
export type Participant = {
    /** The unique identifier for the participant. */
    id: string;
    /** The display name of the participant. */
    username: string;
    /** Whether the participant is currently connected. */
    connected: boolean;
    /** Whether the participant has answered the current question. */
    has_answered: boolean;
};
