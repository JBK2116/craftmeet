// ErrorTypes Enum represents the types of errors returned by the backend
export const ErrorTypes = {
    USERNAME: 'username',
    EMAIL: 'email',
    PASSWORD: 'password',
    TOKEN: 'token',
    SERVER: 'server',
} as const;

export type ErrorTypes = (typeof ErrorTypes)[keyof typeof ErrorTypes];
