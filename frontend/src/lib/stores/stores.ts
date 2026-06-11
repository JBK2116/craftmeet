import { browser } from '$app/environment';
import type { User } from '$lib/types/user';
import { writable } from 'svelte/store';

// check if the user object is stored in browser's local storage
const stored = browser ? localStorage.getItem('user') : null;
// global user object used throughout the applicationapplicaiton
export const user = writable<User | null>(stored ? JSON.parse(stored) : null);

if (browser) {
    user.subscribe((val) => {
        if (val) {
            localStorage.setItem('user', JSON.stringify(val));
        } else {
            localStorage.removeItem('user');
        }
    });
}
