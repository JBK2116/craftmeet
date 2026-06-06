/** All possible question types */
export type QuestionTypes =
    | 'multiple_choice'
    | 'long_answer'
    | 'ranked_voting'
    | 'rating_scale'
    | 'idea_upvote'
    | 'yes_no';

/** All possible question states */
export type QuestionStatus = 'pending' | 'open' | 'closed';

/** A single question object */
export type Question = {
    // IDs
    id: string;
    meeting_id: string;
    // Metadata
    type: QuestionTypes;
    prompt: string;
    position: number;
    status: QuestionStatus;
    // Time
    created_at: string;
    updated_at: string;
};

/** Multiple Choice Sub-Question */
export type MultipleChoiceQuestion = {
    // IDs
    id: string;
    question_id: string;
    // Options
    option_1: string;
    option_2: string;
    option_3: string | null;
    option_4: string | null;
    allow_multiple: boolean;
    // Time
    created_at: string;
    updated_at: string;
};

/** Long Answer Sub-Question */
export type LongAnswerQuestion = {
    // IDs
    id: string;
    question_id: string;
    // Response Length
    max_length: number;
    // Time
    created_at: string;
    updated_at: string;
};
/** Ranked Voting Sub-Question */
export type RankedVotingQuestion = {
    // IDs
    id: string;
    question_id: string;
    // Items
    item_1: string;
    item_2: string;
    item_3: string | null;
    item_4: string | null;
    // Time
    created_at: string;
    updated_at: string;
};

/** Rating Scale Sub-Question */
export type RatingScaleQuestion = {
    // IDs
    id: string;
    question_id: string;
    // Scale Range
    min: number;
    max: number;
    // Time
    created_at: string;
    updated_at: string;
};
