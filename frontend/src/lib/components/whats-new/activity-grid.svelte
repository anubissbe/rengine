<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import Hint from '$lib/components/hint.svelte';
	import { GRID_STEPS, KIND_NOUN, type NewKindKey } from '$lib/config/whats-new';
	import type { NewDay } from '$lib/types/whats-new';

	interface Props {
		days: NewDay[];
		kinds: NewKindKey[];
		from: string | null;
		to: string | null;
		onPick: (from: string | null, to: string | null) => void;
	}

	let { days, kinds, from, to, onPick }: Props = $props();

	const DAY_MS = 86_400_000;
	const WEEKDAYS = ['Mon', '', 'Wed', '', 'Fri', '', ''];
	const OPACITY = ['', '0.3', '0.55', '0.8', '1'];
	const utc = (date: string) => new Date(`${date}T12:00:00Z`);
	const weekday = (date: string) => (utc(date).getUTCDay() + 6) % 7;
	const total = (d: NewDay) => kinds.reduce((n, k) => n + (d.counts[k] ?? 0), 0);
	const today = new Date().toISOString().slice(0, 10);

	let anchor = $state<string | null>(null);
	let hover = $state<string | null>(null);
	let moved = $state(false);

	let cells = $derived.by(() => {
		if (!days.length) return [] as { day: NewDay; col: number; row: number }[];
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
		const byCol = new SvelteMap<number, string>();
		let last = '';
		for (const cell of cells) {
			const label = utc(cell.day.date).toLocaleDateString('en-US', {
				month: 'short',
				timeZone: 'UTC'
			});
			if (label !== last) {
				byCol.set(cell.col, label);
				last = label;
			}
		}
		return [...byCol.entries()].map(([col, label]) => ({ col, label }));
	});
	let range = $derived.by<[string, string] | null>(() => {
		if (anchor && hover && moved) return anchor <= hover ? [anchor, hover] : [hover, anchor];
		if (from) return [from, to ?? from];
		return null;
	});

	function step(n: number): number {
		if (n <= 0 || max <= 0) return 0;
		return Math.max(1, Math.ceil((n / max) * GRID_STEPS));
	}
	function inRange(date: string): boolean {
		return !!range && date >= range[0] && date <= range[1];
	}
	function text(day: NewDay): string {
		const label = utc(day.date).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			timeZone: 'UTC'
		});
		const parts = kinds
			.filter((k) => day.counts[k])
			.map((k) => `${day.counts[k].toLocaleString()} ${KIND_NOUN[k][day.counts[k] === 1 ? 0 : 1]}`);
		return parts.length ? `${label} · ${parts.join(' · ')}` : `${label} · Nothing new`;
	}

	function down(date: string, e: PointerEvent) {
		if (e.button !== 0) return;
		anchor = date;
		hover = date;
		moved = false;
	}
	function enter(date: string) {
		if (!anchor) return;
		hover = date;
		if (date !== anchor) moved = true;
	}
	function up(e: PointerEvent) {
		if (!anchor) return;
		const a = anchor;
		const h = hover ?? a;
		const wasRange = moved;
		anchor = null;
		hover = null;
		moved = false;
		if (wasRange) {
			const [lo, hi] = a <= h ? [a, h] : [h, a];
			onPick(lo, hi === lo ? null : hi);
			return;
		}
		if (e.shiftKey && from) {
			const [lo, hi] = from <= a ? [from, a] : [a, from];
			onPick(lo, hi === lo ? null : hi);
			return;
		}
		if (from === a && !to) onPick(null, null);
		else onPick(a, null);
	}
</script>

<svelte:window onpointerup={up} />

<div class="flex select-none flex-col gap-1">
	<div
		class="ml-8 grid text-2xs text-muted-foreground"
		style="grid-template-columns: repeat({columns}, 0.75rem); column-gap: 0.1875rem"
	>
		{#each months as m (m.col)}
			<span style="grid-column: {m.col + 1}">{m.label}</span>
		{/each}
	</div>
	<div class="flex gap-2">
		<div
			class="grid w-6 text-2xs text-muted-foreground"
			style="grid-template-rows: repeat(7, 0.75rem); row-gap: 0.1875rem"
		>
			{#each WEEKDAYS as w, i (i)}
				<span class="leading-3">{w}</span>
			{/each}
		</div>
		<div
			class="grid touch-none"
			style="grid-template-columns: repeat({columns}, 0.75rem); grid-template-rows: repeat(7, 0.75rem); gap: 0.1875rem; grid-auto-flow: column"
			role="grid"
			aria-label="Days"
		>
			{#each cells as cell (cell.day.date)}
				{@const n = total(cell.day)}
				{@const s = step(n)}
				{@const on = inRange(cell.day.date)}
				<Hint text={text(cell.day)}>
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							class="size-3 rounded-[2px] outline-none focus-visible:ring-2 focus-visible:ring-ring {s ===
							0
								? 'bg-muted/60'
								: ''} {on ? 'ring-2 ring-ring ring-offset-1 ring-offset-background' : ''} {cell.day
								.date === today && !on
								? 'ring-1 ring-border'
								: ''}"
							style={s ? `background: var(--series); opacity: ${OPACITY[s]}` : ''}
							aria-label={text(cell.day)}
							aria-pressed={on}
							onpointerdown={(e) => down(cell.day.date, e)}
							onpointerenter={() => enter(cell.day.date)}
						></button>
					{/snippet}
				</Hint>
			{/each}
		</div>
	</div>
</div>
