/** Multiple Choice Question Response received from backend */
export type MultipleChoiceResponseIn = {
    id: string;
    question_id: string;
    participant_id: string;
    selected_options: number[];
};

/** Multiple Choice Response sent to backend */
export type MultipleChoiceResponseOut = {
    question_id: string;
    participant_id: string;
    selected_options: number[];
};

/** Long Answer Question Response received from backend */
export type LongAnswerResponseIn = {
    id: string;
    question_id: string;
    participant_id: string;
    content: string;
};

/** Long Answer Question Response sent to backend */
export type LongAnswerResponseOut = {
    question_id: string;
    participant_id: string;
    content: string;
};

/** Ranked Voting Question Response received from backend */
export type RankedVotingResponseIn = {
    id: string;
    question_id: string;
    participant_id: string;
    rank_1: number;
    rank_2: number;
    rank_3: number | null;
    rank_4: number | null;
};

/** Ranked Voting Question Response sent to backend */
export type RankedVotingResponseOut = {
    question_id: string;
    participant_id: string;
    rank_1: number;
    rank_2: number;
    rank_3: number | null;
    rank_4: number | null;
};

/** Rating Scale Question Response received from backend */
export type RatingScaleResponseIn = {
    id: string;
    question_id: string;
    participant_id: string;
    value: number;
};

/** Rating Scale Question Response sent to backend */
export type RatingScaleResponseOut = { question_id: string; participant_id: string; value: number };

/** Yes Or No Question Response received from backend */
export type YesNoResponseIn = {
    id: string;
    question_id: string;
    participant_id: string;
    value: boolean;
};

/** Yes Or No Question Response sent to backend */
export type YesNoResponseOut = { question_id: string; participant_id: string; value: boolean };
