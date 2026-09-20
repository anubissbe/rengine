<script lang="ts">
	import Award from '@lucide/svelte/icons/award';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import Library from '@lucide/svelte/icons/library';
	import Target from '@lucide/svelte/icons/target';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import ScanStatusBadge from '$lib/components/scan-status-badge.svelte';
	import ItemRow from './item-row.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { getTargetTypeIcon } from '$lib/config/icons';
	import { SURFACE } from '$lib/config/surface';
	import {
		GONE_KINDS,
		KIND_DIMENSION,
		KIND_LABELS,
		KIND_NOUN,
		NewKind,
		ROWS_SHOWN,
		SELECTABLE_KINDS,
		SubjectKind,
		type NewKindKey
	} from '$lib/config/whats-new';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import type { ScanStatus } from '$lib/types/scan';
	import type { TargetType } from '$lib/types/target';
	import type { NewGroup, NewItem, NewSection } from '$lib/types/whats-new';

	interface Props {
		group: NewGroup;
		rowIndex: (item: NewItem) => number;
		cursorId: string | null;
		isChecked: (id: string) => boolean;
		isBusy: (id: string) => boolean;
		expanded: ReadonlySet<string>;
		onExpand: (key: string) => void;
		onCheck: (item: NewItem, shift: boolean) => void;
		onAddTarget: (item: NewItem) => void;
		onWatch: (item: NewItem) => void;
		onMute: (item: NewItem) => void;
		onScan: (item: NewItem) => void;
		onRemoveTarget: (item: NewItem) => void;
		onScanTarget: (targetId: string) => void;
		onPick: (index: number) => void;
		onOpen: (item: NewItem) => void;
		onAddTargets: (items: NewItem[]) => void;
		addingAll?: boolean;
	}

	let {
		group,
		rowIndex,
		cursorId,
		isChecked,
		isBusy,
		expanded,
		onExpand,
		onCheck,
		onAddTarget,
		onWatch,
		onMute,
		onScan,
		onRemoveTarget,
		onScanTarget,
		onPick,
		onOpen,
		onAddTargets,
		addingAll = false
	}: Props = $props();

	const SHEET_KINDS = new Set<string>([
		NewKind.WEB_ASSET,
		NewKind.SERVICE,
		NewKind.FINDING,
		NewKind.SECRET,
		NewKind.CERT_HOST
	]);
	let collapsed = $state(false);
	let addable = $derived(
		group.sections
			.filter((s) => s.kind === NewKind.SCOPE)
			.flatMap((s) => s.items)
			.filter((i) => i.importable && !i.target_exists)
	);

	let subject = $derived(group.subject);
	let isRun = $derived(subject.kind === SubjectKind.RUN);
	let plain = $derived(
		(subject.kind === SubjectKind.LIBRARY || subject.kind === SubjectKind.TARGETS) &&
			group.sections.length === 1
	);
	let summary = $derived(
		Object.entries(group.counts)
			.filter(([, n]) => n > 0)
			.map(([k, n]) => `${n.toLocaleString()} ${KIND_NOUN[k as NewKindKey][n === 1 ? 0 : 1]}`)
			.join(' · ')
	);
	let SubjectIcon = $derived(
		isRun && subject.target_type
			? getTargetTypeIcon(subject.target_type as TargetType)
			: subject.kind === SubjectKind.PROGRAM
				? Award
				: subject.kind === SubjectKind.TARGETS
					? Target
					: Library
	);
	let subjectHref = $derived(
		isRun && subject.target_id
			? ROUTES.target(subject.target_id)
			: subject.kind === SubjectKind.PROGRAM && subject.handle
				? ROUTES.bountyHub(subject.handle, subject.platform ?? undefined)
				: subject.kind === SubjectKind.LIBRARY
					? ROUTES.bountyHubTab('updates')
					: subject.kind === SubjectKind.TARGETS
						? ROUTES.targets
						: null
	);
	let runLabel = $derived(
		group.scan_started_at
			? `${formatShortDate(group.scan_started_at)} ${new Date(group.scan_started_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`
			: ''
	);

	function allHref(section: NewSection): string | null {
		const dimension = KIND_DIMENSION[section.kind as NewKindKey];
		if (dimension && group.scan_id) {
			const spec = SURFACE[dimension];
			return ROUTES.scanTab(group.scan_id, spec.tab, { [spec.queryParam]: 'is:new' });
		}
		if (section.kind === NewKind.CERT_HOST && subject.watch_id) {
			return ROUTES.bountyWatch(subject.watch_id);
		}
		if (section.kind === NewKind.TARGET) return ROUTES.targets;
		return subject.handle
			? ROUTES.bountyHub(subject.handle, subject.platform ?? undefined)
			: ROUTES.bountyHubTab('updates');
	}

	function shown(section: NewSection): NewItem[] {
		const key = `${group.id}:${section.kind}`;
		return expanded.has(key) ? section.items : section.items.slice(0, ROWS_SHOWN);
	}
</script>

<section class="overflow-clip rounded-xl border bg-card" data-group={group.id}>
	<header
		class="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3.5 py-2.5 {collapsed
			? ''
			: 'border-b'}"
	>
		<div class="flex min-w-0 items-center gap-2 font-semibold">
			<button
				type="button"
				class="flex size-5 items-center justify-center rounded-sm text-muted-foreground hover:bg-muted hover:text-foreground"
				aria-label={collapsed ? 'Expand' : 'Collapse'}
				aria-expanded={!collapsed}
				onclick={() => (collapsed = !collapsed)}
			>
				<ChevronDown class="size-3.5 transition-transform {collapsed ? '-rotate-90' : ''}" />
			</button>
			<SubjectIcon class="size-4 shrink-0 text-muted-foreground" />
			{#if subjectHref}
				<a
					href={subjectHref}
					class="truncate hover:underline {isRun ? 'font-mono text-sm' : 'text-sm'}"
				>
					{subject.label}
				</a>
			{:else}
				<span class="truncate text-sm">{subject.label}</span>
			{/if}
			{#if group.run_label}
				<Badge variant="info">{group.run_label}</Badge>
			{/if}
			{#if subject.kind === SubjectKind.PROGRAM && subject.platform}
				<Badge variant="outline">{bountyVocabulary.label(subject.platform)}</Badge>
				{#if subject.watched}<Badge variant="info">Watched</Badge>{/if}
			{/if}
			{#if isRun && group.scan_status && group.scan_status !== 'completed'}
				<ScanStatusBadge status={group.scan_status as ScanStatus} />
			{/if}
		</div>
		<span class="text-xs text-muted-foreground">
			{summary}{#if group.retired}{summary ? ' · ' : ''}{group.retired.toLocaleString()}
				{KIND_NOUN[NewKind.RETIRED][group.retired === 1 ? 0 : 1]}{/if}
		</span>
		<div class="ml-auto flex items-center gap-1">
			{#if isRun && group.scan_id}
				<a
					href={ROUTES.scan(group.scan_id)}
					class="text-2xs text-muted-foreground tabular-nums hover:underline"
				>
					Run {runLabel}
				</a>
			{:else}
				<span class="text-2xs text-muted-foreground tabular-nums">{relativeTime(group.at)}</span>
			{/if}
			{#if addable.length > 1}
				<LoadingButton
					size="sm"
					class="h-7 px-2.5 text-xs"
					loading={addingAll}
					loadingLabel="Adding"
					onclick={() => onAddTargets(addable)}
				>
					Add {addable.length} targets
				</LoadingButton>
			{/if}
			{#if isRun && group.scan_id && group.previous_scan_id}
				<Button
					variant="ghost"
					size="sm"
					class="h-7 px-2 text-xs"
					href={ROUTES.compare(group.scan_id, group.previous_scan_id)}
				>
					Compare runs
				</Button>
			{/if}
			{#if isRun && subject.target_id}
				<Button
					variant="ghost"
					size="sm"
					class="h-7 px-2 text-xs"
					onclick={() => onScanTarget(subject.target_id ?? '')}
				>
					Scan
				</Button>
			{/if}
		</div>
	</header>

	{#each collapsed ? [] : group.sections as section (section.kind)}
		{@const rows = shown(section)}
		{@const key = `${group.id}:${section.kind}`}
		{@const gone = GONE_KINDS.has(section.kind)}
		<div
			class="flex items-baseline gap-2 px-3.5 pt-2.5 pb-1 text-2xs font-semibold tracking-[0.08em] uppercase {plain
				? 'sr-only'
				: ''} {gone ? 'text-destructive/80' : 'text-muted-foreground'}"
		>
			{KIND_LABELS[section.kind as NewKindKey]}
			<span class="text-xs font-medium tracking-normal normal-case tabular-nums"
				>{section.total.toLocaleString()}</span
			>
			{#if section.total > section.items.length}
				{@const all = allHref(section)}
				{#if all}
					<a
						href={all}
						class="ml-auto text-xs font-normal tracking-normal normal-case hover:underline"
					>
						All {section.total.toLocaleString()}
					</a>
				{/if}
			{/if}
		</div>
		<div class="divide-y divide-border/50">
			{#each rows as item (item.id)}
				<ItemRow
					{item}
					index={rowIndex(item)}
					cursor={cursorId === item.id}
					checked={isChecked(item.id)}
					selectable={SELECTABLE_KINDS.has(item.kind)}
					busy={isBusy(item.id)}
					showTime={!isRun}
					sheet={SHEET_KINDS.has(item.kind) && !!item.scan_id}
					{onPick}
					{onOpen}
					{onCheck}
					{onAddTarget}
					{onWatch}
					{onMute}
					{onScan}
					{onRemoveTarget}
				/>
			{/each}
		</div>
		{#if section.items.length > rows.length}
			<button
				type="button"
				class="w-full py-1.5 text-center text-xs text-muted-foreground hover:bg-muted/50 hover:text-foreground"
				onclick={() => onExpand(key)}
			>
				{(section.items.length - rows.length).toLocaleString()} more
			</button>
		{/if}
	{/each}

	{#if group.retired && group.scan_id && !collapsed}
		<div
			class="flex items-center justify-between gap-3 border-t px-3.5 py-2 text-xs text-muted-foreground"
		>
			<span>
				{group.retired.toLocaleString()}
				{KIND_NOUN[NewKind.RETIRED][group.retired === 1 ? 0 : 1]} in this run
			</span>
			{#if group.previous_scan_id}
				<a href={ROUTES.compare(group.scan_id, group.previous_scan_id)} class="hover:underline"
					>Compare runs</a
				>
			{/if}
		</div>
	{/if}
</section>
