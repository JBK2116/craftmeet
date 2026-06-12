import type { User } from '$lib/types/user';
import { writable } from 'svelte/store';

// global user object used throughout the applicationapplicaiton
export const user = writable<User | null>(null);
