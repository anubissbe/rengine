import { api } from './client';
import type { OastRead, OastTest, OastUpdate } from '$lib/types/oast';

export const oastApi = {
	async get(): Promise<OastRead> {
		return api.get<OastRead>('/oast');
	},

	async update(data: OastUpdate): Promise<OastRead> {
		return api.patch<OastRead>('/oast', data);
	},

	async reset(): Promise<OastRead> {
		return api.post<OastRead>('/oast/reset', {});
	},

	async test(): Promise<OastTest> {
		return api.post<OastTest>('/oast/test', {});
	}
};
