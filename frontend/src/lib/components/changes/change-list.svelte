<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import History from '@lucide/svelte/icons/history';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { ChangeKind, KIND_ICONS, TONE_NODE, type ChangeKindKey } from '$lib/config/changes';
	import { exactToken } from '$lib/utilities/scan-insights';
	import type { ChangeItem } from '$lib/types/changes';

	interface Props {
		items: ChangeItem[];
		loading?: boolean;
		emptyTitle?: string;
		truncated?: boolean;
		total?: number;
	}

	let {
		items,
		loading = false,
		emptyTitle = 'No changes',
		truncated = false,
		total = 0
	}: Props = $props();

	interface DayGroup {
		key: string;
		label: string;
		items: ChangeItem[];
	}

	const fmtTime = (iso: string) =>
		new Date(iso).toLocaleTimeString('en-US', {
			hour: 'numeric',
			minute: '2-digit',
			timeZone: 'UTC'
		});
	const dayKey = (iso: string) => iso.slice(0, 10);
	const dayLabel = (key: string) => {
		const today = new Date().toISOString().slice(0, 10);
		if (key === today) return 'Today';
		const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
		if (key === yesterday) return 'Yesterday';
		return new Date(`${key}T12:00:00Z`).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			timeZone: 'UTC'
		});
	};

	let groups = $derived.by<DayGroup[]>(() => {
		const out: DayGroup[] = [];
		for (const item of items) {
			const key = dayKey(item.at);
			const last = out.at(-1);
			if (last && last.key === key) last.items.push(item);
			else out.push({ key, label: dayLabel(key), items: [item] });
		}
		return out;
	});

	function href(item: ChangeItem): string | null {
		switch (item.kind) {
			case ChangeKind.SCANNED_ASSET:
				return item.scan_id
					? ROUTES.scanTab(item.scan_id, 'web-assets', { q: exactToken('host', item.value) })
					: null;
			case ChangeKind.WATCH_HOST:
				return item.scan_id
					? ROUTES.scan(item.scan_id)
					: item.watch_id
						? ROUTES.bountyWatch(item.watch_id)
						: null;
			case ChangeKind.TARGET:
				return item.target_id ? ROUTES.target(item.target_id) : null;
			default:
				return item.handle ? ROUTES.bountyHub(item.handle, item.platform ?? undefined) : null;
		}
	}

	const badgeVariant = (tone: string) =>
		tone === 'hot' ? 'destructive' : tone === 'new' ? 'info' : 'secondary';
</script>

{#if loading && items.length === 0}
	<div class="relative pl-[10px]">
		<div class="absolute top-0 bottom-4 left-[10px] w-px bg-border/40"></div>
		{#each { length: 6 } as _, i (i)}
			<div class="relative flex gap-3 pb-4">
				<Skeleton class="z-[1] mt-px size-5 shrink-0 rounded-full" />
				<div class="flex-1 space-y-1.5 py-0.5">
					<Skeleton class="h-3 rounded" style="width:{72 - i * 8}%" />
					<Skeleton class="h-2.5 w-24 rounded" />
				</div>
			</div>
		{/each}
	</div>
{:else if items.length === 0}
	<EmptyState icon={History} title={emptyTitle} class="py-16" />
{:else}
	<div class="transition-opacity {loading ? 'opacity-60' : ''}">
		{#each groups as group (group.key)}
			<div
				data-day={group.key}
				class="sticky top-0 z-10 flex scroll-mt-24 items-center gap-2 bg-background/95 py-1.5 backdrop-blur"
			>
				<span class="text-2xs font-semibold tracking-[0.1em] text-muted-foreground/80 uppercase">
					{group.label}
				</span>
				<span class="text-2xs text-muted-foreground/60 tabular-nums">{group.items.length}</span>
				<div class="h-px flex-1 bg-border/40"></div>
			</div>
			<ol class="relative">
				<div class="absolute top-0 bottom-2 left-[10px] w-px bg-border/40"></div>
				{#each group.items as item (item.id)}
					{@const Icon = KIND_ICONS[item.kind as ChangeKindKey] ?? History}
					{@const link = href(item)}
					<li class="relative flex items-start gap-3 py-2">
						<div class="relative z-[1] flex w-5 shrink-0 justify-center">
							<div
								class="mt-px flex size-5 items-center justify-center rounded-full {TONE_NODE[
									item.tone
								] ?? TONE_NODE.neutral}"
							>
								<Icon class="size-3" />
							</div>
						</div>
						<div class="flex min-w-0 flex-1 flex-col gap-1">
							<div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
								<Badge variant={badgeVariant(item.tone)} class="font-normal">{item.label}</Badge>
								{#if link}
									<a
										href={link}
										class="inline-flex min-w-0 items-center gap-1 font-mono text-sm wrap-anywhere hover:underline"
									>
										{item.value}
										<ArrowUpRight class="size-3 shrink-0 text-muted-foreground" />
									</a>
								{:else}
									<span class="min-w-0 font-mono text-sm wrap-anywhere">{item.value}</span>
								{/if}
								{#if item.detail}
									<span class="truncate text-xs text-muted-foreground">{item.detail}</span>
								{/if}
							</div>
							<div
								class="flex flex-wrap items-center gap-x-2 gap-y-1 text-2xs text-muted-foreground"
							>
								<span class="font-mono tabular-nums">{fmtTime(item.at)}</span>
								{#if item.source_label}
									<span>· {item.source_label}</span>
								{/if}
								{#if item.program_name && item.handle}
									<a
										href={ROUTES.bountyHub(item.handle, item.platform ?? undefined)}
										class="hover:text-foreground hover:underline">· {item.program_name}</a
									>
								{/if}
								{#if item.target_value && item.target_id && item.kind !== ChangeKind.TARGET}
									<a
										href={ROUTES.target(item.target_id)}
										class="hover:text-foreground hover:underline">· {item.target_value}</a
									>
								{/if}
							</div>
						</div>
					</li>
				{/each}
			</ol>
		{/each}
		{#if truncated}
			<p class="py-3 text-center text-xs text-muted-foreground">
				Newest {items.length.toLocaleString()} of {total.toLocaleString()}.
			</p>
		{/if}
	</div>
{/if}
