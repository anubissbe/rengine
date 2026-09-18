// mirrors shared/definitions/whats_new.py
import Globe from '@lucide/svelte/icons/globe';
import EthernetPort from '@lucide/svelte/icons/ethernet-port';
import Bug from '@lucide/svelte/icons/bug';
import KeyRound from '@lucide/svelte/icons/key-round';
import ShieldCheck from '@lucide/svelte/icons/shield-check';
import Award from '@lucide/svelte/icons/award';
import Radar from '@lucide/svelte/icons/radar';
import Target from '@lucide/svelte/icons/target';
import CircleMinus from '@lucide/svelte/icons/circle-minus';
import type { IconComponent } from './icons';
import { SurfaceDimension } from './surface';

export const NewKind = {
	WEB_ASSET: 'web_asset',
	SERVICE: 'service',
	FINDING: 'finding',
	SECRET: 'secret',
	SCOPE: 'scope',
	PROGRAM: 'program',
	CERT_HOST: 'cert_host',
	TARGET: 'target',
	OUT_OF_SCOPE: 'out_of_scope',
	RETIRED: 'retired'
} as const;
export type NewKindKey = (typeof NewKind)[keyof typeof NewKind];

export const KIND_ORDER: NewKindKey[] = [
	NewKind.WEB_ASSET,
	NewKind.SERVICE,
	NewKind.FINDING,
	NewKind.SECRET,
	NewKind.SCOPE,
	NewKind.PROGRAM,
	NewKind.CERT_HOST,
	NewKind.TARGET,
	NewKind.OUT_OF_SCOPE,
	NewKind.RETIRED
];

export const KIND_LABELS: Record<NewKindKey, string> = {
	[NewKind.WEB_ASSET]: 'Web assets',
	[NewKind.SERVICE]: 'Services',
	[NewKind.FINDING]: 'Findings',
	[NewKind.SECRET]: 'Secrets',
	[NewKind.SCOPE]: 'In scope',
	[NewKind.PROGRAM]: 'Programs',
	[NewKind.CERT_HOST]: 'Certificate hosts',
	[NewKind.TARGET]: 'Targets',
	[NewKind.OUT_OF_SCOPE]: 'Out of scope',
	[NewKind.RETIRED]: 'Retired'
};

export const KIND_NOUN: Record<NewKindKey, [string, string]> = {
	[NewKind.WEB_ASSET]: ['web asset', 'web assets'],
	[NewKind.SERVICE]: ['service', 'services'],
	[NewKind.FINDING]: ['finding', 'findings'],
	[NewKind.SECRET]: ['secret', 'secrets'],
	[NewKind.SCOPE]: ['asset in scope', 'assets in scope'],
	[NewKind.PROGRAM]: ['program', 'programs'],
	[NewKind.CERT_HOST]: ['certificate host', 'certificate hosts'],
	[NewKind.TARGET]: ['target', 'targets'],
	[NewKind.OUT_OF_SCOPE]: ['asset out of scope', 'assets out of scope'],
	[NewKind.RETIRED]: ['web asset retired', 'web assets retired']
};

export const KIND_ICONS: Record<NewKindKey, IconComponent> = {
	[NewKind.WEB_ASSET]: Globe,
	[NewKind.SERVICE]: EthernetPort,
	[NewKind.FINDING]: Bug,
	[NewKind.SECRET]: KeyRound,
	[NewKind.SCOPE]: ShieldCheck,
	[NewKind.PROGRAM]: Award,
	[NewKind.CERT_HOST]: Radar,
	[NewKind.TARGET]: Target,
	[NewKind.OUT_OF_SCOPE]: CircleMinus,
	[NewKind.RETIRED]: CircleMinus
};

export const SCAN_KINDS: ReadonlySet<string> = new Set([
	NewKind.WEB_ASSET,
	NewKind.SERVICE,
	NewKind.FINDING,
	NewKind.SECRET
]);
export const BOUNTY_KINDS: ReadonlySet<string> = new Set([
	NewKind.SCOPE,
	NewKind.PROGRAM,
	NewKind.CERT_HOST,
	NewKind.TARGET,
	NewKind.OUT_OF_SCOPE
]);
export const GONE_KINDS: ReadonlySet<string> = new Set([NewKind.OUT_OF_SCOPE, NewKind.RETIRED]);
export const SELECTABLE_KINDS: ReadonlySet<string> = new Set([
	NewKind.SCOPE,
	NewKind.CERT_HOST,
	NewKind.WEB_ASSET,
	NewKind.TARGET
]);

export const KIND_DIMENSION: Partial<Record<NewKindKey, SurfaceDimension>> = {
	[NewKind.WEB_ASSET]: SurfaceDimension.WEB_ASSETS,
	[NewKind.SERVICE]: SurfaceDimension.SERVICES,
	[NewKind.FINDING]: SurfaceDimension.VULNERABILITIES,
	[NewKind.SECRET]: SurfaceDimension.SECRETS
};

export const NewBasis = { MARK: 'mark', WINDOW: 'window', DAYS: 'days' } as const;

export const SubjectKind = {
	RUN: 'run',
	PROGRAM: 'program',
	LIBRARY: 'library',
	TARGETS: 'targets'
} as const;

export const ProgramRing = { ENGAGED: 'engaged', LIBRARY: 'library' } as const;
export type ProgramRingKey = (typeof ProgramRing)[keyof typeof ProgramRing];
export const RING_LABELS: Record<ProgramRingKey, string> = {
	[ProgramRing.ENGAGED]: 'Programs with my targets',
	[ProgramRing.LIBRARY]: 'Every program'
};

export const Fact = {
	SENSITIVE: 'sensitive',
	CRITICAL: 'critical',
	KEV: 'kev',
	NOT_TARGET: 'not_target',
	ANSWERING: 'answering',
	NOT_SCANNED: 'not_scanned',
	TARGETS: 'targets',
	RUNS: 'runs'
} as const;

export const FACT_LABELS: Record<string, [string, string]> = {
	[Fact.SENSITIVE]: ['sensitive', 'sensitive'],
	[Fact.CRITICAL]: ['critical', 'critical'],
	[Fact.KEV]: ['known exploited', 'known exploited'],
	[Fact.NOT_TARGET]: ['not a target', 'not targets'],
	[Fact.ANSWERING]: ['answering', 'answering'],
	[Fact.NOT_SCANNED]: ['not scanned', 'not scanned'],
	[Fact.TARGETS]: ['target', 'targets']
};

export const NEW_WINDOWS = [
	{ key: 'since', label: 'Since caught up' },
	{ key: '24h', label: '24h' },
	{ key: '7d', label: '7d' },
	{ key: '30d', label: '30d' }
] as const;
export type NewWindowKey = (typeof NEW_WINDOWS)[number]['key'];
export const SINCE_KEY: NewWindowKey = 'since';

export const NewSource = { ALL: 'all', TARGETS: 'targets', BOUNTY: 'bounty' } as const;
export type NewSourceKey = (typeof NewSource)[keyof typeof NewSource];
export const SOURCE_OPTIONS: { key: NewSourceKey; label: string }[] = [
	{ key: NewSource.ALL, label: 'All' },
	{ key: NewSource.TARGETS, label: 'My targets' },
	{ key: NewSource.BOUNTY, label: 'Bounty Hub' }
];
export const SOURCE_KINDS: Record<NewSourceKey, ReadonlySet<string>> = {
	[NewSource.ALL]: new Set(KIND_ORDER),
	[NewSource.TARGETS]: new Set([...SCAN_KINDS, NewKind.RETIRED]),
	[NewSource.BOUNTY]: BOUNTY_KINDS
};

export const NewTab = { NEW: 'new', VISUAL: 'visual' } as const;
export type NewTabKey = (typeof NewTab)[keyof typeof NewTab];
export const NEW_TABS: { key: NewTabKey; label: string }[] = [
	{ key: NewTab.NEW, label: 'New' },
	{ key: NewTab.VISUAL, label: 'Visual changes' }
];

export const VISUAL_FIELD_LABELS: Record<string, string> = {
	http_status: 'Status',
	page_title: 'Title',
	tech: 'Technology',
	webserver: 'Server'
};
export const VISUAL_MAX_DISTANCE = 64;
export const VISUAL_KEYS: { key: string; does: string }[] = [
	{ key: 'j / k', does: 'move' },
	{ key: 'Enter', does: 'wipe' },
	{ key: 's', does: 'scan' },
	{ key: '/', does: 'filter' }
];

export const GRID_STEPS = 4;
export const ROWS_SHOWN = 5;

export const NEW_KEYS: { key: string; does: string; bounty?: boolean }[] = [
	{ key: 'j / k', does: 'move' },
	{ key: 'x', does: 'select' },
	{ key: 'Enter', does: 'open' },
	{ key: 'a', does: 'add target', bounty: true },
	{ key: 's', does: 'scan' },
	{ key: 'm', does: 'mute', bounty: true },
	{ key: '/', does: 'filter' }
];
