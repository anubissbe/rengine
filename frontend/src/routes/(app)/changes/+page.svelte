<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import * as Select from '$lib/components/ui/select';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import ChangeList from '$lib/components/changes/change-list.svelte';
	import { changesApi } from '$lib/api/changes';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { watchesStore } from '$lib/stores/watches.svelte';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { Capability } from '$lib/config/capabilities';
	import { routeLabels } from '$lib/config/routes';
	import {
		BOUNTY_KINDS,
		CHANGE_MODES,
		CHANGE_WINDOWS,
		ChangeBasis,
		DEFAULT_CHANGE_WINDOW,
		KIND_LABELS,
		KIND_ORDER,
		type ChangeMode,
		type ChangeWindow
	} from '$lib/config/changes';
	import { SELECT_NONE } from '$lib/constants';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { ChangeFeed } from '$lib/types/changes';

	const MODE_KEYS = new Set<string>(CHANGE_MODES.map((m) => m.key));
	const WINDOW_KEYS = new Set<string>(CHANGE_WINDOWS.map((w) => w.key));
	const ALL = 'all';

	const initial = page.url.searchParams;
	let mode = $state<ChangeMode>(
		MODE_KEYS.has(initial.get('mode') ?? '') ? (initial.get('mode') as ChangeMode) : 'since'
	);
	let range = $state<ChangeWindow>(
		WINDOW_KEYS.has(initial.get('window') ?? '')
			? (initial.get('window') as ChangeWindow)
			: DEFAULT_CHANGE_WINDOW
	);
	let targetId = $state(initial.get('target') ?? '');
	let program = $state(
		initial.get('handle') && initial.get('platform')
			? `${initial.get('platform')}:${initial.get('handle')}`
			: ''
	);
	const splitProgram = (v: string): [string, string] => {
		const i = v.indexOf(':');
		return i < 0 ? ['', ''] : [v.slice(0, i), v.slice(i + 1)];
	};
	const KIND_KEYS = new Set<string>(KIND_ORDER);
	let kind = $state(
		KIND_KEYS.has(initial.get('kind') ?? '') ? (initial.get('kind') as string) : ALL
	);

	let feed = $state<ChangeFeed | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let sinceAt = $state<string | null>(null);
	let fallbackWindow = $state<string | null>(null);
	let markedFor = '';
	let reqId = 0;

	interface Visit {
		projectId: string;
		since: string | null;
		window: string | null;
		at: number;
	}
	const VISIT_TTL_MS = 12 * 60 * 60 * 1000;

	function readVisit(id: string): Visit | null {
		try {
			const raw = sessionStorage.getItem(STORAGE_KEYS.changesVisit);
			const v = raw ? (JSON.parse(raw) as Visit) : null;
			return v && v.projectId === id && Date.now() - v.at < VISIT_TTL_MS ? v : null;
		} catch {
			return null;
		}
	}
	function writeVisit(v: Visit) {
		try {
			sessionStorage.setItem(STORAGE_KEYS.changesVisit, JSON.stringify(v));
		} catch {
			// ignore
		}
	}

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let projectSlug = $derived(projectsStore.activeProject?.slug ?? '');
	let bounty = $derived(capabilitiesStore.has(Capability.BOUNTY_PROGRAMS));
	let kinds = $derived(KIND_ORDER.filter((k) => bounty || !BOUNTY_KINDS.has(k)));
	let targetLabel = $derived(
		targetsStore.targets.find((t) => t.id === targetId)?.target_value ??
			feed?.items.find((i) => i.target_id === targetId)?.target_value ??
			(targetId ? 'Target' : '')
	);
	let programLabel = $derived.by(() => {
		if (!program) return '';
		const [platform, handle] = splitProgram(program);
		return (
			watchesStore.watches.find((w) => w.platform === platform && w.handle === handle)
				?.program_name ?? handle
		);
	});
	let total = $derived(
		feed
			? kind === ALL
				? Object.values(feed.counts).reduce((a, b) => a + b, 0)
				: (feed.counts[kind] ?? 0)
			: 0
	);
	let headline = $derived.by(() => {
		if (!feed) return '';
		const what = total === 1 ? '1 change' : `${total.toLocaleString()} changes`;
		if (feed.basis === ChangeBasis.MARK) return `${what} since last visit`;
		return `${what} in the ${CHANGE_WINDOWS.find((w) => w.key === feed?.window)?.text ?? 'window'}`;
	});
	let subline = $derived.by(() => {
		if (!feed) return '';
		const at = new Date(feed.since);
		const stamp = `${formatShortDate(at)} ${at.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
		if (feed.basis === ChangeBasis.MARK) return `Last visit ${stamp}`;
		return mode === 'since' ? `No earlier visit · from ${stamp}` : `From ${stamp}`;
	});

	function syncUrl() {
		try {
			const sp = new SvelteURLSearchParams();
			if (mode !== 'since') sp.set('mode', mode);
			if (mode === 'timeline' && range !== DEFAULT_CHANGE_WINDOW) sp.set('window', range);
			if (targetId) sp.set('target', targetId);
			if (program) {
				const [platform, handle] = splitProgram(program);
				sp.set('platform', platform);
				sp.set('handle', handle);
			}
			if (kind !== ALL) sp.set('kind', kind);
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, page.state);
		} catch {
			// ignore
		}
	}

	async function load() {
		if (!projectId) return;
		const my = ++reqId;
		loading = true;
		error = null;
		const [platform, handle] = splitProgram(program);
		try {
			const res = await changesApi.feed(projectId, {
				since: mode === 'since' ? (sinceAt ?? undefined) : undefined,
				window: mode === 'timeline' ? range : (fallbackWindow ?? undefined),
				target_id: targetId || undefined,
				platform: platform || undefined,
				handle: handle || undefined,
				kinds: kind === ALL ? undefined : kind
			});
			if (my !== reqId) return;
			feed = res;
			if (mode === 'since') {
				if (res.basis === ChangeBasis.MARK) sinceAt = res.since;
				else fallbackWindow = res.window;
				if (markedFor !== projectId) {
					markedFor = projectId;
					writeVisit({ projectId, since: sinceAt, window: fallbackWindow, at: Date.now() });
					void changesApi.markSeen(projectId).catch(() => {});
				}
			}
		} catch (e) {
			if (my !== reqId) return;
			error = e instanceof Error ? e.message : 'Changes not loaded';
		} finally {
			if (my === reqId) loading = false;
		}
	}

	let loadedFor = '';
	$effect(() => {
		const id = projectId;
		void mode;
		void range;
		void targetId;
		void program;
		void kind;
		untrack(() => {
			if (id && loadedFor !== id) {
				loadedFor = id;
				const visit = readVisit(id);
				sinceAt = visit?.since ?? null;
				fallbackWindow = visit?.window ?? null;
				if (visit) markedFor = id;
				feed = null;
			}
			syncUrl();
			void load();
		});
	});

	$effect(() => {
		const id = projectId;
		const slug = projectSlug;
		if (!id) return;
		untrack(() => {
			if (slug) void targetsStore.fetchAll(slug);
			if (bounty && watchesStore.fetchedProjectId !== id) void watchesStore.fetch(id);
		});
	});

	function setMode(next: ChangeMode) {
		if (next !== mode) mode = next;
	}
</script>

<svelte:head><title>{routeLabels.changes} · reNgine</title></svelte:head>

<div class="flex flex-col gap-4 p-4">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="flex flex-col gap-1">
			<h1 class="text-xl font-semibold">{routeLabels.changes}</h1>
			{#if feed}
				<p class="text-sm text-muted-foreground">{headline} · {subline}</p>
			{/if}
		</div>
		<ToggleGroup.Root
			type="single"
			value={mode}
			onValueChange={(v) => v && setMode(v as ChangeMode)}
			variant="outline"
			size="sm"
			aria-label="Mode"
		>
			{#each CHANGE_MODES as option (option.key)}
				<ToggleGroup.Item value={option.key} class="h-8 px-3 text-xs font-normal">
					{option.label}
				</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>
	</div>

	<div class="flex flex-wrap items-center gap-2">
		{#if mode === 'timeline'}
			<ToggleGroup.Root
				type="single"
				value={range}
				onValueChange={(v) => v && (range = v as ChangeWindow)}
				variant="outline"
				size="sm"
				aria-label="Window"
			>
				{#each CHANGE_WINDOWS as option (option.key)}
					<ToggleGroup.Item value={option.key} class="h-8 px-2.5 text-xs font-normal">
						{option.label}
					</ToggleGroup.Item>
				{/each}
			</ToggleGroup.Root>
		{/if}
		<Select.Root
			type="single"
			value={targetId || SELECT_NONE}
			onValueChange={(v) => (targetId = v === SELECT_NONE ? '' : v)}
		>
			<Select.Trigger class="h-8 w-56 text-xs" aria-label="Target">
				{targetId ? targetLabel : 'All targets'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value={SELECT_NONE} label="All targets">All targets</Select.Item>
				{#if targetId && !targetsStore.targets.some((t) => t.id === targetId)}
					<Select.Item value={targetId} label={targetLabel}>{targetLabel}</Select.Item>
				{/if}
				{#each targetsStore.targets as t (t.id)}
					<Select.Item value={t.id} label={t.target_value}>{t.target_value}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		{#if bounty && (watchesStore.watches.length || program)}
			<Select.Root
				type="single"
				value={program || SELECT_NONE}
				onValueChange={(v) => (program = v === SELECT_NONE ? '' : v)}
			>
				<Select.Trigger class="h-8 w-56 text-xs" aria-label="Program">
					{program ? programLabel : 'All programs'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value={SELECT_NONE} label="All programs">All programs</Select.Item>
					{#each watchesStore.watches as w (w.id)}
						<Select.Item value={`${w.platform}:${w.handle}`} label={w.program_name}>
							{w.program_name}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		{/if}
		{#if targetId || program}
			<Button
				variant="ghost"
				size="sm"
				class="h-8 gap-1 text-xs"
				onclick={() => {
					targetId = '';
					program = '';
				}}
			>
				<X class="size-3.5" /> Clear
			</Button>
		{/if}
	</div>

	<div class="overflow-clip rounded-xl border bg-card">
		<CountTabs
			tabs={[
				{ key: ALL, label: 'All' },
				...kinds
					.filter((k) => k === kind || (feed?.counts[k] ?? 0) > 0)
					.map((k) => ({ key: k, label: KIND_LABELS[k] }))
			]}
			counts={feed
				? {
						[ALL]: Object.values(feed.counts).reduce((a, b) => a + b, 0),
						...feed.counts
					}
				: null}
			value={kind}
			onChange={(k) => (kind = k)}
		/>
		<div class="px-4 pb-2">
			{#if error}
				<div class="flex flex-col items-center gap-3 py-16">
					<p class="text-sm text-muted-foreground">{error}</p>
					<Button size="sm" variant="outline" onclick={() => load()}>Retry</Button>
				</div>
			{:else}
				<ChangeList
					items={feed?.items ?? []}
					{loading}
					{total}
					truncated={feed?.truncated ?? false}
					emptyTitle={mode === 'since' && feed?.basis === ChangeBasis.MARK
						? 'Nothing new since last visit'
						: 'No changes'}
				/>
			{/if}
		</div>
	</div>
</div>
