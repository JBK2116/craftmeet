/** A Participant in a meeting. */
export type Participant = {
    /** The display name of the participant. */
    username: string;
    /** The unique identifier for the participant. */
    id: string;
    /** The time the participant joined the meeting. */
    joined_at: Date;
    /** Whether the participant is currently connected. */
    connected: boolean;
    /** Whether the participant has answered the current question. */
    has_answered: boolean;
};
