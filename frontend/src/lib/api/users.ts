import { api } from './client';

export interface UserSummary {
	id: string;
	username: string;
}

export interface UserAccount {
	id: string;
	username: string;
	email: string;
	is_active: boolean;
	is_superuser: boolean;
	totp_enabled: boolean;
}

const cache = new Map<string, Promise<UserSummary>>();

export const usersApi = {
	list(): Promise<UserAccount[]> {
		return api.get<UserAccount[]>('/users?limit=500');
	},

	getSummary(userId: string): Promise<UserSummary> {
		const cached = cache.get(userId);
		if (cached) return cached;
		const request = api.get<UserSummary>(`/users/${userId}/summary`).catch((err) => {
			cache.delete(userId);
			throw err;
		});
		cache.set(userId, request);
		return request;
	}
};
