/** Multiple Choice Question Response */
export type MultipleChoiceResponse = {
    // IDs
    id: string;
    question_id: string;
    participant_id: string;
    // Selected
    selected_options: number[];
    // Time
    created_at: string;
    updated_at: string;
};

/** Long Answer Question Response */
export type LongAnswerResponse = {
    // IDs
    id: string;
    question_id: string;
    participant_id: string;
    // Content
    content: string;
    // Time
    created_at: string;
    updated_at: string;
};

/** Ranked Voting Question Response */
export type RankedVotingResponse = {
    // IDs
    id: string;
    question_id: string;
    participant_id: string;
    // Ranking
    rank_1: number;
    rank_2: number;
    rank_3: number;
    rank_4: number;
    // Time
    created_at: string;
    updated_at: string;
};

/** Rating Scale Question Response */
export type RatingScaleResponse = {
    // IDs
    id: string;
    question_id: string;
    participant_id: string;
    // Chosen Value
    value: number;
};

/** Participant Idea Submission */
export type IdeaSubmission = {
    // IDs
    id: string;
    question_id: string;
    participant_id: string;
    // Idea Content
    content: string;
};

/** Participant Idea Vote */
export type IdeaVote = {
    // IDs
    id: string;
    submission_id: string;
    participant_id: string;
};

/** Yes Or No Question Response */
export type YesNoResponse = {
    // IDs
    id: string;
    question_id: string;
    participant_id: string;
    // Answer
    value: boolean;
};
