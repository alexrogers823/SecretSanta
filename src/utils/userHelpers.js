// Older users created before the name split may not have a last name yet
export const getFullName = user => [user?.first_name, user?.last_name].filter(Boolean).join(' ')
