// mirrors shared/definitions/changes.py
import Globe from '@lucide/svelte/icons/globe';
import ShieldCheck from '@lucide/svelte/icons/shield-check';
import Award from '@lucide/svelte/icons/award';
import Target from '@lucide/svelte/icons/target';
import Radar from '@lucide/svelte/icons/radar';
import type { IconComponent } from './icons';

export const ChangeKind = {
	SCANNED_ASSET: 'scanned_asset',
	SCOPE_ASSET: 'scope_asset',
	PROGRAM: 'program',
	WATCH_HOST: 'watch_host',
	TARGET: 'target'
} as const;
export type ChangeKindKey = (typeof ChangeKind)[keyof typeof ChangeKind];

export const KIND_ORDER: ChangeKindKey[] = [
	ChangeKind.SCANNED_ASSET,
	ChangeKind.SCOPE_ASSET,
	ChangeKind.PROGRAM,
	ChangeKind.WATCH_HOST,
	ChangeKind.TARGET
];

export const KIND_LABELS: Record<ChangeKindKey, string> = {
	[ChangeKind.SCANNED_ASSET]: 'Scanned assets',
	[ChangeKind.SCOPE_ASSET]: 'In-scope assets',
	[ChangeKind.PROGRAM]: 'Programs',
	[ChangeKind.WATCH_HOST]: 'Watched hosts',
	[ChangeKind.TARGET]: 'Targets'
};

export const KIND_ICONS: Record<ChangeKindKey, IconComponent> = {
	[ChangeKind.SCANNED_ASSET]: Globe,
	[ChangeKind.SCOPE_ASSET]: ShieldCheck,
	[ChangeKind.PROGRAM]: Award,
	[ChangeKind.WATCH_HOST]: Radar,
	[ChangeKind.TARGET]: Target
};

export const BOUNTY_KINDS: ReadonlySet<string> = new Set([
	ChangeKind.SCOPE_ASSET,
	ChangeKind.PROGRAM,
	ChangeKind.WATCH_HOST,
	ChangeKind.TARGET
]);

export const ChangeBasis = { MARK: 'mark', WINDOW: 'window' } as const;

export const CHANGE_MODES = [
	{ key: 'since', label: 'Since last visit' },
	{ key: 'timeline', label: 'Timeline' }
] as const;
export type ChangeMode = (typeof CHANGE_MODES)[number]['key'];

export const CHANGE_WINDOWS = [
	{ key: '7d', label: '7d', text: 'last 7 days' },
	{ key: '30d', label: '30d', text: 'last 30 days' },
	{ key: '90d', label: '90d', text: 'last 90 days' }
] as const;
export type ChangeWindow = (typeof CHANGE_WINDOWS)[number]['key'];
export const DEFAULT_CHANGE_WINDOW: ChangeWindow = '30d';

export const TONE_NODE: Record<string, string> = {
	new: 'bg-info/10 text-info ring-1 ring-info/30',
	hot: 'bg-destructive/10 text-destructive ring-1 ring-destructive/40',
	neutral: 'bg-muted text-muted-foreground ring-1 ring-border'
};

export const GRID_STEPS = 4;
