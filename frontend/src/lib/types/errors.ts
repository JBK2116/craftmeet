// ErrorTypes Enum represents the types of errors returned by the backend
export const ErrorTypes = {
    BODY: 'body',
    INVALID_CREDENTIALS: 'invalid_credentials',
    USERNAME: 'username',
    EMAIL: 'email',
    EMAIL_ALREADY_EXISTS: 'email_already_exists',
    EMAIL_NOT_VERIFIED: 'email_not_verified',
    PASSWORD: 'password',
    CONFIRM_PASSWORD: 'confirm_password',
    TOKEN: 'token',
    VERIFY_EMAIL_TOKEN_COOLDOWN: 'verify_email_token_cooldown',
    SERVER: 'server',
} as const;

export type ErrorTypes = (typeof ErrorTypes)[keyof typeof ErrorTypes];

/**
 * Custom error class representing an authentication failure.
 */
export class AuthError extends Error {
    constructor() {
        super('AUTH_FAILED');
    }
}

export class RateLimitedError extends Error {
    constructor() {
        super('You are being rate limited. Please slow down and try again shortly.');
    }
}
