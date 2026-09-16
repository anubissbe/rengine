<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import type { DashboardReadiness } from '$lib/types/dashboard';
	import Launcher from './launcher.svelte';
	import ReadinessStrip from './readiness-strip.svelte';

	interface Props {
		readiness: DashboardReadiness | null;
	}

	let { readiness }: Props = $props();
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<div class="px-5 py-5">
		<Launcher
			heading="No targets in this project"
			sub="Add a domain, IP address, IP range, URL or ASN."
		/>
	</div>
	<ReadinessStrip {readiness} />
</Card.Root>
