import type { MeetingPlan } from './meeting';

/** A single user instance. */
export type User = {
    id: string;
    username: string | null;
    email: string;
    // OAUTH
    google_id: string | null;
    // Meeting Stat
    live_meeting: boolean;
    total_meetings_month: number;
    total_meetings: number;
    total_participants: number;
    meeting_plan: MeetingPlan;
    // verification_status
    is_verified: boolean;
    // Time
    created_at: string;
    updated_at: string;
};
