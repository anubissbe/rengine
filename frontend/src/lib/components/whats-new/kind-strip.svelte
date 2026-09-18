<script lang="ts">
	import {
		FACT_LABELS,
		GONE_KINDS,
		KIND_ICONS,
		KIND_LABELS,
		type NewKindKey
	} from '$lib/config/whats-new';
	import type { NewDay } from '$lib/types/whats-new';

	interface Props {
		kinds: NewKindKey[];
		counts: Record<string, number>;
		facts: Record<string, Record<string, number>>;
		selected: ReadonlySet<string>;
		flat?: boolean;
		daily?: NewDay[];
		onToggle: (kind: NewKindKey) => void;
	}

	let { kinds, counts, facts, selected, flat = false, daily = [], onToggle }: Props = $props();

	const WEEKS = 13;
	let weekly = $derived.by(() => {
		const out: Record<string, number[]> = {};
		if (!daily.length) return out;
		for (const kind of kinds) {
			const bars = Array<number>(WEEKS).fill(0);
			for (let i = 0; i < daily.length; i++) {
				const week = WEEKS - 1 - Math.floor((daily.length - 1 - i) / 7);
				if (week >= 0) bars[week] += daily[i].counts[kind] ?? 0;
			}
			out[kind] = bars;
		}
		return out;
	});

	let shown = $derived(kinds.filter((k) => (counts[k] ?? 0) > 0 || selected.has(k)));

	function fact(kind: string): string | null {
		const entries = Object.entries(facts[kind] ?? {}).filter(([, n]) => n > 0);
		if (entries.length === 0) return null;
		return entries
			.map(([key, n]) => `${n.toLocaleString()} ${FACT_LABELS[key]?.[n === 1 ? 0 : 1] ?? key}`)
			.join(' · ');
	}
</script>

{#if shown.length > 0}
	<div
		class="grid grid-cols-[repeat(auto-fit,minmax(9.5rem,1fr))] overflow-clip {flat
			? ''
			: 'rounded-xl border bg-card'}"
		role="group"
		aria-label="Kinds"
	>
		{#each shown as kind (kind)}
			{@const Icon = KIND_ICONS[kind]}
			{@const n = counts[kind] ?? 0}
			{@const on = selected.has(kind)}
			{@const gone = GONE_KINDS.has(kind)}
			{@const sub = fact(kind)}
			<button
				type="button"
				class="group/tile -mr-px -mb-px flex flex-col gap-1.5 border-r border-b px-3.5 py-3 text-left transition-colors hover:bg-muted/60 focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {on
					? 'bg-muted/40 shadow-[inset_0_-2px_0_var(--primary)]'
					: ''}"
				aria-pressed={on}
				onclick={() => onToggle(kind)}
			>
				<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
					<Icon class="size-3.5" />
					{KIND_LABELS[kind]}
				</span>
				<span
					class="text-xl leading-none font-semibold tabular-nums {gone
						? 'text-muted-foreground'
						: ''}"
				>
					{n.toLocaleString()}
				</span>
				<span class="min-h-4 text-2xs text-muted-foreground">{sub ?? ''}</span>
				{#if weekly[kind]?.some((n) => n > 0)}
					{@const bars = weekly[kind]}
					{@const top = Math.max(1, ...bars)}
					<span class="flex h-3.5 items-end gap-px" aria-hidden="true">
						{#each bars as n, i (i)}
							<span
								class="w-1.5 rounded-[1px] {n ? '' : 'bg-muted'}"
								style="height: {n ? Math.max(15, (n / top) * 100) : 15}%; {n
									? 'background: var(--series); opacity: 0.7'
									: ''}"
							></span>
						{/each}
					</span>
				{/if}
			</button>
		{/each}
	</div>
{/if}
