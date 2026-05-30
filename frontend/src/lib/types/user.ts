import type { MeetingPlan } from './meeting';

/** A single user instance. */
export type User = {
    id: string; // uuid
    name: string; // username
    email: string; // email
    plan: MeetingPlan; // subscription plan
    meetings_used_this_month: number; // meeting count for month
    total_meetings_run: number; // total meeting count for lifecycle
    total_participants: number; // total participant count for lifecycle
    joined_at: string; // ISO timestamp
};
