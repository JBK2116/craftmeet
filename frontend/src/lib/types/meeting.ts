/** Lifecycle state of a meeting. */
export type MeetingStatus = 'live' | 'draft' | 'completed';

/** Subscription plan types. */
export type MeetingPlan = 'free' | 'pro' | 'team';

/** A single meeting session created by a host. */
export type Meeting = {
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
    // Status
    started_at: string | null;
    ended_at: string | null;
    participant_cap: number;
    // Time
    created_at: string;
    updated_at: string;
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
    // Time
    created_at: string;
    updated_at: string;
};
