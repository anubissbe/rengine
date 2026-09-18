<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import { GRID_STEPS, KIND_LABELS, KIND_ORDER, type ChangeKindKey } from '$lib/config/changes';
	import type { ChangeDay } from '$lib/types/changes';

	interface Props {
		days: ChangeDay[];
		kinds?: ChangeKindKey[];
		selected?: string | null;
		onPick?: (date: string) => void;
	}

	let { days, kinds = KIND_ORDER, selected = null, onPick }: Props = $props();

	const DAY_MS = 86_400_000;
	const utc = (date: string) => new Date(`${date}T12:00:00Z`);
	const weekday = (date: string) => (utc(date).getUTCDay() + 6) % 7;
	const total = (d: ChangeDay) => kinds.reduce((n, k) => n + (d.counts[k] ?? 0), 0);

	let cells = $derived.by(() => {
		if (!days.length) return [] as { day: ChangeDay; col: number; row: number }[];
		const first = utc(days[0].date);
		const offset = weekday(days[0].date);
		return days.map((day) => {
			const index = Math.round((utc(day.date).getTime() - first.getTime()) / DAY_MS) + offset;
			return { day, col: Math.floor(index / 7), row: index % 7 };
		});
	});
	let columns = $derived(cells.length ? cells[cells.length - 1].col + 1 : 0);
	let max = $derived(Math.max(0, ...days.map(total)));
	let months = $derived.by(() => {
		const out: { col: number; label: string }[] = [];
		let last = '';
		for (const cell of cells) {
			const label = utc(cell.day.date).toLocaleDateString('en-US', {
				month: 'short',
				timeZone: 'UTC'
			});
			if (label !== last && cell.row === 0) {
				out.push({ col: cell.col, label });
				last = label;
			}
		}
		return out;
	});

	function step(n: number): number {
		if (n <= 0 || max <= 0) return 0;
		return Math.max(1, Math.ceil((n / max) * GRID_STEPS));
	}
	const OPACITY = ['', '0.3', '0.55', '0.8', '1'];

	function text(day: ChangeDay): string {
		const label = utc(day.date).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			timeZone: 'UTC'
		});
		const parts = kinds
			.filter((k) => day.counts[k])
			.map((k) => `${day.counts[k].toLocaleString()} ${KIND_LABELS[k].toLowerCase()}`);
		return parts.length ? `${label} · ${parts.join(' · ')}` : `${label} · Nothing new`;
	}
</script>

<div class="flex flex-col gap-1">
	<div
		class="grid text-2xs text-muted-foreground"
		style="grid-template-columns: repeat({columns}, 0.75rem); column-gap: 0.1875rem"
	>
		{#each months as m (m.col)}
			<span style="grid-column: {m.col + 1}">{m.label}</span>
		{/each}
	</div>
	<div
		class="grid"
		style="grid-template-columns: repeat({columns}, 0.75rem); grid-template-rows: repeat(7, 0.75rem); gap: 0.1875rem; grid-auto-flow: column"
	>
		{#each cells as cell (cell.day.date)}
			{@const n = total(cell.day)}
			{@const s = step(n)}
			<Hint text={text(cell.day)}>
				{#snippet child(props)}
					<button
						{...props}
						type="button"
						class="size-3 rounded-[2px] {s === 0 ? 'bg-muted/60' : ''} {selected === cell.day.date
							? 'ring-2 ring-ring ring-offset-1 ring-offset-background'
							: ''} {n ? 'cursor-pointer' : 'cursor-default'}"
						style="grid-column: {cell.col + 1}; grid-row: {cell.row + 1}; {s
							? `background: var(--series); opacity: ${OPACITY[s]}`
							: ''}"
						aria-label={text(cell.day)}
						onclick={() => n && onPick?.(cell.day.date)}
					></button>
				{/snippet}
			</Hint>
		{/each}
	</div>
</div>
