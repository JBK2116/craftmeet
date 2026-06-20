import type {
    LongAnswerResponseIn,
    MultipleChoiceResponseIn,
    RankedVotingResponseIn,
    RatingScaleResponseIn,
    YesNoResponseIn,
} from './response';

/** All possible question types */
export type QuestionTypes =
    | 'multiple_choice'
    | 'long_answer'
    | 'ranked_voting'
    | 'rating_scale'
    | 'yes_no';

/** All possible question states */
export type QuestionStatus = 'pending' | 'open' | 'closed';

/** A single question object received from backend */
export type QuestionIn = {
    // IDs
    id: string;
    meeting_id: string;
    // Metadata
    type: QuestionTypes;
    prompt: string;
    position: number;
    status: QuestionStatus;
    sub_question:
        | MultipleChoiceQuestionIn
        | LongAnswerQuestionIn
        | RankedVotingQuestionIn
        | RatingScaleQuestionIn
        | YesNoQuestionIn;
};

/** Multiple Choice Sub-Question received from backend */
export type MultipleChoiceQuestionIn = {
    // IDs
    id: string;
    question_id: string;
    // Options
    option_1: string;
    option_2: string;
    option_3: string | null;
    option_4: string | null;
    allow_multiple: boolean;
    responses: MultipleChoiceResponseIn[];
};

/** Long Answer Sub-Question received from backend */
export type LongAnswerQuestionIn = {
    // IDs
    id: string;
    question_id: string;
    // Response Length
    max_length: number;
    responses: LongAnswerResponseIn[];
};
/** Ranked Voting Sub-Question received from backend */
export type RankedVotingQuestionIn = {
    // IDs
    id: string;
    question_id: string;
    // Items
    item_1: string;
    item_2: string;
    item_3: string | null;
    item_4: string | null;
    responses: RankedVotingResponseIn[];
};

/** Rating Scale Sub-Question received from backend */
export type RatingScaleQuestionIn = {
    // IDs
    id: string;
    question_id: string;
    // Scale Range
    min: number;
    max: number;
    responses: RatingScaleResponseIn[];
};

/** YesNo Sub-Question received from backend */
export type YesNoQuestionIn = {
    // IDs
    id: string;
    question_id: string;
    responses: YesNoResponseIn[];
};

/** Updated question sent to backend */
export type QuestionUpdate = {
    id: string | null;
    type: QuestionTypes;
    prompt: string;
    position: number;
    sub_question:
        | YesNoQuestionOut
        | RatingScaleQuestionOut
        | RankedVotingQuestionOut
        | LongAnswerQuestionOut
        | MultipleChoiceQuestionOut;
};
/** Question sent to backend */
export type QuestionOut = {
    type: QuestionTypes;
    prompt: string;
    position: number;
    sub_question:
        | YesNoQuestionOut
        | RatingScaleQuestionOut
        | RankedVotingQuestionOut
        | LongAnswerQuestionOut
        | MultipleChoiceQuestionOut;
};

/** YesNo Sub-Question sent to backend */
export type YesNoQuestionOut = {};

/** RatingScaleQuestion sent to backend */
export type RatingScaleQuestionOut = { min: number; max: number };

/** RankedVotingQuestion sent to backend */
export type RankedVotingQuestionOut = {
    item_1: string;
    item_2: string;
    item_3: string | null;
    item_4: string | null;
};

/** LongAnswerQuestion sent to backend */
export type LongAnswerQuestionOut = { max_length: number };

/** MultipleChoiceQuestion sent to backend */
export type MultipleChoiceQuestionOut = {
    option_1: string;
    option_2: string;
    option_3: string | null;
    option_4: string | null;
    allow_multiple: boolean;
};
