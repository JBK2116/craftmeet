import type { MeetingIn } from '$lib/types/meeting';
import type { User } from '$lib/types/user';
import { writable } from 'svelte/store';

// global user object used throughout the application
export const user = writable<User | null>(null);

// meetings received from the backend used throughout the application
export const meetings = writable<MeetingIn[]>([]);
