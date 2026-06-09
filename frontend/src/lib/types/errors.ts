// ErrorTypes Enum represents the types of errors returned by the backend
export const ErrorTypes = {
    INVALID_CREDENTIALS: 'invalid_credentials',
    USERNAME: 'username',
    EMAIL: 'email',
    EMAIL_ALREADY_EXISTS: 'email_already_exists',
    EMAIL_NOT_VERIFIED: 'email_not_verified',
    PASSWORD: 'password',
    TOKEN: 'token',
    VERIFY_EMAIL_TOKEN_COOLDOWN: 'verify_email_token_cooldown',
    SERVER: 'server',
} as const;

export type ErrorTypes = (typeof ErrorTypes)[keyof typeof ErrorTypes];
