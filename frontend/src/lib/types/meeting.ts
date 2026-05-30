/** Lifecycle state of a meeting. */
export type MeetingStatus = 'live' | 'draft' | 'completed';

/** Subscription plan types. */
export type MeetingPlan = 'free' | 'pro' | 'team';

/** A single meeting session created by a host. */
export type Meeting = {
    id: string; // uuid
    room_code: string; // access code
    title: string; // title
    description?: string; // description
    question_count: number; // total questions in this meeting
    participant_count?: number; // total unique participants (completed meetings)
    participant_cap: number; // max participant count
    status: MeetingStatus; // current status
    ended_at?: string; // ISO timestamp, present when status is 'completed'
    created_at: string; // ISO timestamp
    started_at?: string; // ISO timestamp, present when status is 'live' or 'completed'
};
