import type { QuestionIn, QuestionOut, QuestionUpdate } from './question';

/** Lifecycle state of a meeting. */
export type MeetingStatus = 'live' | 'draft' | 'completed';

/** Lifecycle state of a meeting from a live/presenter perspective. */
export type LiveMeetingStatus = 'lobby' | 'question' | 'ended';

/** Subscription plan types. */
export type MeetingPlan = 'free' | 'pro' | 'team';

/** Current mood of a live meeting */
export type Mood = 'positive' | 'neutral' | 'negative' | 'mixed' | 'disengaged';

/** Current snapshot of the live meeting */
export type MeetingSnapshot = {
    /** Mood of the live meeting */
    mood: Mood;
    /** Things that need attention */
    attention_flag: string;
    /** Next suggested question prompt */
    suggested_question_prompt: string;
    /** Snapshots created at time (ISO8601) */
    created_at: string;
};

/** A single meeting session created by a host and received from backend. */
export type MeetingIn = {
    // IDs
    id: string;
    user_id: string;
    // Metadata
    title: string;
    description: string | null;
    total_questions: number;
    room_code: string;
    status: MeetingStatus;
    stats: Stat;
    duration: number;
    // Status
    started_at: string | null;
    ended_at: string | null;
    participant_cap: number;
    // questions
    questions: QuestionIn[];
    // Time
    created_at: string;
    updated_at: string;
};

/** A single meeting session that is being updated after client side changes */
export type MeetingUpdate = {
    title: string;
    description: string | null;
    participant_cap: number;
    duration: number;
    questions: QuestionUpdate[];
};

/** A single meeting session created by a host and sent to the backend */
export type MeetingOut = {
    title: string;
    description: string | null;
    participant_cap: number;
    duration: number;
    questions: QuestionOut[];
};

/** Statistics related to a corresponding meeting */
export type Stat = {
    // IDs
    id: string;
    meeting_id: string;
    // Stats
    total_participants: number;
    total_questions_asked: number;
    total_responses_received: number;
    average_response_rate: number;
    duration_seconds: number | null;
};
