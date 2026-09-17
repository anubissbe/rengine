import type { ChangeFeed, ChangeFeedParams, ChangeMark } from '$lib/types/changes';
import { api } from './client';

function query(params: Record<string, unknown>): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		search.set(key, String(value));
	}
	return `?${search.toString()}`;
}

export const changesApi = {
	feed(projectId: string, params: ChangeFeedParams = {}): Promise<ChangeFeed> {
		return api.get<ChangeFeed>(`/changes${query({ project_id: projectId, ...params })}`);
	},
	markSeen(projectId: string): Promise<ChangeMark> {
		return api.post<ChangeMark>(`/changes/seen${query({ project_id: projectId })}`, {});
	}
};
