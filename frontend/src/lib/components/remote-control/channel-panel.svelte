<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import ChannelRail from './channel-rail.svelte';
	import ConnectSection from './connect-section.svelte';
	import PairingRequests from './pairing-requests.svelte';
	import ChatsSection from './chats-section.svelte';
	import CommandsSection from './commands-section.svelte';
	import ActivitySection from './activity-section.svelte';
	import { remoteControl } from '$lib/stores/remote-control.svelte';
	import { CHANNEL_VIEW_LABELS, CHANNEL_VIEWS, type ChannelView } from '$lib/config/channels';
	import type { ChannelKind } from '$lib/config/channels';
	import type { ChannelStatus } from '$lib/types/remote-control';

	interface Props {
		channel: ChannelKind;
		status: ChannelStatus;
		canAdmin: boolean;
		now: number;
		view: ChannelView;
		onStart: () => void;
		onView: (view: ChannelView) => void;
	}

	let { channel, status, canAdmin, now, view, onStart, onView }: Props = $props();

	const pending = $derived(remoteControl.pending);
	const tabs = CHANNEL_VIEWS.map((key) => ({ key, label: CHANNEL_VIEW_LABELS[key] }));
	const counts = $derived<Record<string, number | null>>({
		overview: canAdmin ? status.chats_active || null : null,
		commands: remoteControl.commands.length || null,
		activity: remoteControl.calls.length || null
	});
</script>

<div class="flex flex-col gap-4">
	<div class="border-b">
		<CountTabs {tabs} value={view} {counts} onChange={(k) => onView(k as ChannelView)} />
	</div>

	{#if view === 'overview'}
		<Card.Root class="grid gap-0 py-0 lg:grid-cols-[minmax(0,1fr)_18.5rem]">
			<div class="flex min-w-0 flex-col divide-y px-5 lg:border-r">
				{#if !status.configured}
					<ConnectSection {channel} {canAdmin} />
				{:else}
					{#if canAdmin && pending.length}
						<PairingRequests {status} requests={pending} {now} />
					{/if}
					<ChatsSection {status} {canAdmin} {onStart} />
				{/if}
			</div>
			<div class="border-t px-5 py-5 lg:sticky lg:top-4 lg:self-start lg:border-t-0">
				<ChannelRail {channel} {status} {canAdmin} />
			</div>
		</Card.Root>
	{:else if view === 'commands'}
		<Card.Root class="gap-0 px-5 py-0">
			<CommandsSection commands={remoteControl.commands} />
		</Card.Root>
	{:else}
		<Card.Root class="gap-0 px-5 py-0">
			<ActivitySection calls={remoteControl.calls} commands={remoteControl.commands} />
		</Card.Root>
	{/if}
</div>
