// mirrors shared/definitions/changes.py
import Globe from '@lucide/svelte/icons/globe';
import ShieldCheck from '@lucide/svelte/icons/shield-check';
import ShieldMinus from '@lucide/svelte/icons/shield-minus';
import Award from '@lucide/svelte/icons/award';
import Target from '@lucide/svelte/icons/target';
import Radar from '@lucide/svelte/icons/radar';
import type { IconComponent } from './icons';

export const ChangeKind = {
	WEB_ASSET: 'web_asset',
	HOST: 'host',
	SCOPE_ADDED: 'scope_added',
	SCOPE_REMOVED: 'scope_removed',
	PROGRAM: 'program',
	TARGET: 'target'
} as const;
export type ChangeKindKey = (typeof ChangeKind)[keyof typeof ChangeKind];

export const KIND_ORDER: ChangeKindKey[] = [
	ChangeKind.WEB_ASSET,
	ChangeKind.HOST,
	ChangeKind.SCOPE_ADDED,
	ChangeKind.SCOPE_REMOVED,
	ChangeKind.PROGRAM,
	ChangeKind.TARGET
];

export const KIND_LABELS: Record<ChangeKindKey, string> = {
	[ChangeKind.WEB_ASSET]: 'Web assets',
	[ChangeKind.HOST]: 'In-scope hosts',
	[ChangeKind.SCOPE_ADDED]: 'Came into scope',
	[ChangeKind.SCOPE_REMOVED]: 'Left scope',
	[ChangeKind.PROGRAM]: 'Programs',
	[ChangeKind.TARGET]: 'Targets'
};

export const KIND_ICONS: Record<ChangeKindKey, IconComponent> = {
	[ChangeKind.WEB_ASSET]: Globe,
	[ChangeKind.HOST]: Radar,
	[ChangeKind.SCOPE_ADDED]: ShieldCheck,
	[ChangeKind.SCOPE_REMOVED]: ShieldMinus,
	[ChangeKind.PROGRAM]: Award,
	[ChangeKind.TARGET]: Target
};

export const BOUNTY_KINDS: ReadonlySet<string> = new Set([
	ChangeKind.HOST,
	ChangeKind.SCOPE_ADDED,
	ChangeKind.SCOPE_REMOVED,
	ChangeKind.PROGRAM
]);

export const ChangeBasis = { MARK: 'mark', WINDOW: 'window' } as const;

export const CHANGE_MODES = [
	{ key: 'since', label: 'Since last visit' },
	{ key: 'timeline', label: 'Timeline' }
] as const;
export type ChangeMode = (typeof CHANGE_MODES)[number]['key'];

export const CHANGE_WINDOWS = [
	{ key: '24h', label: '24h', text: 'last 24 hours' },
	{ key: '7d', label: '7d', text: 'last 7 days' },
	{ key: '14d', label: '14d', text: 'last 14 days' },
	{ key: '30d', label: '30d', text: 'last 30 days' },
	{ key: '90d', label: '90d', text: 'last 90 days' }
] as const;
export type ChangeWindow = (typeof CHANGE_WINDOWS)[number]['key'];
export const DEFAULT_CHANGE_WINDOW: ChangeWindow = '7d';

export const TONE_NODE: Record<string, string> = {
	new: 'bg-info/10 text-info ring-1 ring-info/30',
	hot: 'bg-destructive/10 text-destructive ring-1 ring-destructive/40',
	neutral: 'bg-muted text-muted-foreground ring-1 ring-border'
};
