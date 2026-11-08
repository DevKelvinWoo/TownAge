# Session chat

`ATownAgeGameMode` selects `ATownAgePlayerController`. The controller owns the
native UMG `UTownAgeChatWidget` and the chat RPCs; no widget assets or external
packages are required. `UMG`, `Slate` and `SlateCore` are engine modules.
Keep the editable-box style in widget-owned storage: UE 5.8's
`UEditableTextBox::SetWidgetStyle` passes the caller's style address to Slate.
Passing a temporary style after construction leaves a dangling brush pointer.

## Controls and layout

- PC: translucent conversation panel at the bottom left. Enter opens the input;
  Enter or Send submits and returns to gameplay. Escape or Close preserves the
  draft and returns to gameplay. The chat button also opens the composer.
- Android/iOS: CHAT sits above the left joystick, inset from the screen edge.
  Tapping opens a panel at the top left to leave space for the virtual keyboard.
  Send and Close have at least 48 physical viewport pixels of height, accounting
  for UMG DPI scaling. SafeZone applies the platform's safe-area padding.
- `-faketouches` previews this arrangement on Windows. It does not verify an
  Android/iOS keyboard, packaging, safe-area reporting or physical device speed.
- Input is a native editable text box with platform IME/virtual keyboard support.
  Dismissing the keyboard preserves text; Send explicitly submits it. A keyboard
  Enter commit also submits. Truncation preserves UTF-16 surrogate pairs.
- Chat input gates the pawn's direct WASD, touch movement, sprint and interaction
  polling as well as controller move/look input. Touches continue to be sampled
  to prevent a held interaction touch from becoming a fresh press after closing.

## Multiplayer and limits

The owning controller sends a reliable server RPC. Authority rejects oversized
requests, strips control characters and directional overrides, trims empty
messages, enforces one accepted message per second, and obtains a bounded
display name from the server's PlayerState. A client never supplies a sender.
The input draft is cleared only after server acceptance. Rejection preserves it;
an acknowledgement never clears a different draft typed while waiting.
The server sends a reliable owning-client RPC to every TownAge controller in
the same world, including the listen host and sender. This also works with a
dedicated server, which creates no chat widget. Door streaming stays in the
same world and does not interrupt chat.

Messages are plain text, including markup-looking strings. The maximum is 200
UTF-16 code units, not 200 grapheme clusters. Each local widget keeps 80 rows;
scrolling up pauses automatic scrolling while the composer is open. Mobile
shows an unread count while closed, excluding the sender's own messages.
History is local and transient, with no replay to late joiners, save, external
service, cross-server delivery, private channels, moderation or block list.

## Verification

Build `TownAgeEditor Win64 Development`, then run:

```powershell
& 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/TownAge.uproject" -unattended -nullrhi -nosound '-ExecCmds=Automation RunTests TownAge;Quit' '-TestExit=Automation Test Queue Empty' '-log=ChatAutomation.log'
```

`TownAge.Chat.Rules` covers Korean, empty/control input, literal markup, lengths,
directional overrides, valid/invalid UTF-16 pairs and cooldown boundaries.
Existing TownAge stamina, interaction, touch and door tests also run.

For transport/UI verification, start two **separate processes** of UnrealEditor
with this project and `-game -windowed -nosound`. The host URL is
`/Game/Maps/L_CharacterTest?listen`; the client URL is `127.0.0.1`. Give the client
`-faketouches`. Use native keyboard/touch input, rather than Python ProcessEvent,
to exercise remote RPC callspace. Confirm both directions, Korean text, escape,
typing WASD without moving, unread counts and joystick separation. Test small
landscape windows and resize. Close the temporary game processes afterward.

Local evidence is in `Saved/Logs/ChatAutomation.log`, `ChatHost.log` and
`ChatClient.log`; visual iteration notes are in `.omx/state/chat`. Test logs and
binary/media assets are not published. Physical Android/iOS tests, packet loss
and dedicated-server packaging are separate checks.

Local validation passed: editor/UHT build; all six TownAge automation tests;
native two-process Korean delivery in both directions; mobile CHAT/Send clicks,
Escape and reopening with the draft retained; accepted draft clearing and counter
reset; movement gating while typing; desktop 1280x720 and mobile-layout 960x540
inspection. The temporary style pointer crash found during visual testing was
repaired and the same open/type/send/reopen path passed afterward. Android/iOS
SDKs are not configured on this machine; no mobile package/device claim is made.
