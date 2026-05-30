import type { Meeting } from './meeting';
import type { User } from './user';

// This file stores mock data until the backend is implemented
export const mockUser: User = {
    id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    name: 'Alex Rivera',
    email: 'alex@example.com',
    plan: 'free',
    meetings_used_this_month: 3,
    total_meetings_run: 12,
    total_participants: 87,
    joined_at: '2025-01-15T10:00:00Z',
};

export const mockMeetings: Meeting[] = [
    // LIVE
    {
        id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        title: 'Engineering All-Hands',
        description: 'Monthly sync covering sprint progress, blockers, and team announcements.',
        status: 'live',
        room_code: 'LIMA42',
        participant_cap: 50,
        question_count: 8,
        created_at: '2026-05-29T09:00:00Z',
        started_at: '2026-05-29T09:05:00Z',
    },

    // DRAFT
    {
        id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
        title: 'Product Roadmap Review — H2',
        description: 'Walk through second-half priorities and gather input on trade-offs.',
        status: 'draft',
        room_code: 'ROMEO5',
        participant_cap: 25,
        question_count: 10,
        created_at: '2026-05-28T14:30:00Z',
    },
    {
        // Edge case: just created, no questions added yet
        id: 'c3d4e5f6-a7b8-9012-cdef-123456789012',
        title: 'New Hire Orientation Q&A',
        status: 'draft',
        room_code: 'INDIA8',
        participant_cap: 10,
        question_count: 0,
        created_at: '2026-05-29T08:15:00Z',
    },

    // COMPLETED
    {
        // Near-capacity, long session, has description
        id: 'd4e5f6a7-b8c9-0123-defa-234567890123',
        title: 'Q1 OKR Retrospective',
        description: 'End-of-quarter review of objectives and key results across all departments.',
        status: 'completed',
        room_code: 'OSCAR11',
        participant_cap: 50,
        question_count: 12,
        participant_count: 47,
        created_at: '2026-04-15T10:00:00Z',
        started_at: '2026-04-15T10:07:00Z',
        ended_at: '2026-04-15T11:45:00Z',
    },
    {
        // At full capacity, short session
        id: 'e5f6a7b8-c9d0-1234-efab-345678901234',
        title: 'Incident Post-Mortem',
        status: 'completed',
        room_code: 'TANGO9',
        participant_cap: 5,
        question_count: 4,
        participant_count: 5,
        created_at: '2026-05-20T16:00:00Z',
        started_at: '2026-05-20T16:05:00Z',
        ended_at: '2026-05-20T16:28:00Z',
    },
    {
        // Low attendance relative to cap
        id: 'f6a7b8c9-d0e1-2345-fabc-456789012345',
        title: 'Customer Feedback Deep Dive',
        description: 'Structured Q&A following the May user research interviews.',
        status: 'completed',
        room_code: 'KILO66',
        participant_cap: 25,
        question_count: 7,
        participant_count: 9,
        created_at: '2026-05-05T15:00:00Z',
        started_at: '2026-05-05T15:10:00Z',
        ended_at: '2026-05-05T16:05:00Z',
    },
    {
        // Small team, moderate session
        id: 'a7b8c9d0-e1f2-3456-abcd-567890123456',
        title: 'Design Sprint Retrospective',
        status: 'completed',
        room_code: 'PAPA33',
        participant_cap: 10,
        question_count: 5,
        participant_count: 7,
        created_at: '2026-05-12T13:00:00Z',
        started_at: '2026-05-12T13:02:00Z',
        ended_at: '2026-05-12T13:38:00Z',
    },
];
