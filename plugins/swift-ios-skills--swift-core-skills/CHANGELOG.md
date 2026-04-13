# Changelog

## v3.1.0

### Swift 6.3 update

- Bump all skills from Swift 6.2 to Swift 6.3 targeting.
- Add `async defer` (SE-0493) and clock epochs (SE-0473) to `swift-concurrency`.
- Add `@c` (SE-0495), `@specialized` (SE-0460), `@inline(always)` guarantee (SE-0496), `@export` (SE-0497), `@section`/`@used` (SE-0492), and module selectors (SE-0491) to `swift-language`.
- Add warning-severity issues (ST-0013), programmatic test cancellation (ST-0016), exit test value capturing (ST-0012), and image attachments (ST-0014) to `swift-testing`.
- Integrate Swift 6.3 features into existing topical sections instead of version-siloed sections.
- Rename version-based reference files to topic-based names (`swift-6-2-concurrency.md` → `concurrency-patterns.md`, `swift-6-3-features.md` → `swift-attributes-interop.md`, `swift-6-3-testing.md` → `testing-advanced.md`).
- Update README badge and description for Swift 6.3.
- Bump marketplace bundle versions to 3.1.0.

## v3.0.0

### Skill renames

12 existing skills renamed to use Apple Kit framework names for consistency:

- `live-activities` -> `activitykit`
- `mapkit-location` -> `mapkit`
- `photos-camera-media` -> `photokit`
- `homekit-matter` -> `homekit`
- `callkit-voip` -> `callkit`
- `metrickit-diagnostics` -> `metrickit`
- `pencilkit-drawing` -> `pencilkit`
- `passkit-wallet` -> `passkit`
- `musickit-audio` -> `musickit`
- `cloudkit-sync` -> `cloudkit`
- `eventkit-calendar` -> `eventkit`
- `realitykit-ar` -> `realitykit`

### New skills

19 new Apple Kit framework skills, all grounded in official Apple documentation:

- `avkit` -- AVPlayerViewController, VideoPlayer, Picture-in-Picture, AirPlay, subtitles
- `gamekit` -- Game Center, leaderboards, achievements, real-time and turn-based multiplayer
- `cryptokit` -- SHA256, HMAC, AES-GCM, ChaChaPoly, P256/Curve25519 signing, Secure Enclave
- `pdfkit` -- PDFView, PDFDocument, annotations, text search, form filling, thumbnails
- `paperkit` -- PaperMarkupViewController, markup editing, drawing, shapes (iOS 26)
- `spritekit` -- SKScene, SKSpriteNode, SKAction, physics, particles, SpriteView
- `scenekit` -- SCNView, SCNScene, 3D geometry, materials, lighting, physics, SceneView
- `financekit` -- Apple Card, Apple Cash, Wallet orders, transactions, account balances
- `accessorysetupkit` -- Privacy-preserving BLE/Wi-Fi accessory discovery, picker UI
- `adattributionkit` -- Privacy-preserving ad attribution, postbacks, conversion values
- `carplay` -- CarPlay templates, navigation, audio, communication, EV charging apps
- `appmigrationkit` -- Cross-platform data transfer, export/import extensions (iOS 26)
- `browserenginekit` -- Alternative browser engines (EU), process management, web content
- `dockkit` -- DockAccessoryManager, camera subject tracking, motor control, framing
- `sensorkit` -- Research-grade sensor data, ambient light, keyboard metrics (approved studies)
- `tabletopkit` -- Multiplayer spatial board games, pieces, cards, dice (visionOS)
- `relevancekit` -- Widget relevance signals, time/location-based providers (watchOS 26)
- `audioaccessorykit` -- Audio accessory features, automatic switching (iOS 26.4)
- `cryptotokenkit` -- TKTokenDriver, TKSmartCard, security tokens, certificate-based auth

### Bundle changes

- Add `apple-kit-skills` bundle containing all 39 Apple Kit framework skills.
- Add `ios-gaming-skills` bundle containing `gamekit`, `spritekit`, `scenekit`, `tabletopkit`.
- Distribute new skills into existing themed bundles.
- Update `all-ios-skills` count from 57 to 76.
- Fix all renamed skill paths across all existing bundles.

### Other changes

- Remove PaperKit content from `pencilkit` (now standalone `paperkit` skill).
- Update README catalog, descriptions, counts, install commands, and upgrade guidance.
- Bump Claude marketplace bundle versions to 3.0.0.

### API accuracy fixes

- Fix 15+ incorrect deprecation claims across skills (RotationGesture, .tabItem, .navigationBarLeading/Trailing, IntentTimelineProvider, original StoreKit APIs were not deprecated).
- Correct API usage in activitykit, background-processing, cloudkit, debugging-instruments, energykit, shareplay-activities, swift-concurrency, and swift-testing.
- Clarify BrowserEngineKit EU/Japan distribution requirements.

### Structural improvements

- Add missing scope statements to debugging-instruments, swiftui-liquid-glass, and swiftui-performance.
- Trim photokit SKILL.md to under 500-line limit.
- Refactor metrickit and device-integrity to extract deep detail into reference files.
- Expand thin reference files in swiftui-layout-components, swiftui-performance, and swiftui-webkit.
- Add Contents sections to reference files in background-processing, swiftui-gestures, and swiftui-navigation.
- Convert all reference paths from backtick to markdown link syntax across all 76 skills.

### Link and cross-reference fixes

- Normalize all Sosumi documentation paths to lowercase.
- Repair broken self-anchor links across skills.
- Replace stale pre-rename skill names in reference file intros.
- Remove broken reference to background-websocket.md in ios-networking.
- Fix malformed key-path syntax in swiftui-performance reference.
- Clarify themed bundle purpose in README (context window management, not disk savings).
- Update apple-kit-skills description to include CarPlay.

## v2.2.0

- Add `swiftui-webkit`, a new SwiftUI skill for native WebKit-for-SwiftUI APIs including `WebView`, `WebPage`, navigation policies, JavaScript calls, observable page state, and custom URL schemes.
- Narrow `swiftui-uikit-interop` back to generic interop guidance by removing `WKWebView` and `SFSafariViewController` recipes from its representable reference file and demoting web-content ownership.
- Update the README catalog and marketplace metadata to include `swiftui-webkit`, add it to the `swiftui-skills` and `all-ios-skills` bundles, and raise the total skill count from 56 to 57.
- Bump Claude marketplace bundle versions to 2.2.0.

## v2.1.1

- Consolidate repeated sibling-skill cross-references in `swiftui-patterns` into a single scope-boundary note; remove redundant redirect sections and sibling-skill routing from frontmatter description.
- Consolidate repeated `apple-on-device-ai` cross-references in `coreml` and remove cross-skill file paths that violated self-containment.
- Bump Claude marketplace bundle versions to 2.1.1.

## v2.1.0

- Rename `codable-patterns` to `swift-codable` to improve discoverability and align it with the repo's `swift-*` core-language taxonomy.
- Tighten discovery wording for `swift-codable`, `alarmkit`, `app-clips`, and `app-intents` in skill metadata and the README catalog.
- Clarify installation guidance in `README.md`, including skills CLI usage and the direct install command for all skills.
- Remove stale MCP appendix/tool-note sections from `swiftui-liquid-glass`, `swift-testing`, and `swiftui-performance`; keep Release-build and real-device profiling guidance inline in the performance skill.
- Add `firebase-debug.log` to `.gitignore`.
- Bump Claude marketplace bundle versions to 2.1.0.

## v2.0.1

- Update `swiftui-animation` to cover `.animation(_:body:)` alongside `.animation(_:value:)`, and tighten wording around bare `.animation(_:)` and scoped transactions to match Apple docs.
- Switch the repository license to PolyForm Perimeter 1.0.0 and update the README badge/license text.
- Add `.playwright-mcp` and `tmp` to `.gitignore`.
- Bump Claude marketplace bundle versions to 2.0.1.

## v2.0.0

### New skills (33 added)

**SwiftUI (3)**
- `swiftui-gestures` — Tap, drag, magnify, rotate, long press, simultaneous and sequential gestures
- `swiftui-layout-components` — Grid, LazyVGrid, Layout protocol, ViewThatFits, custom layouts
- `swiftui-navigation` — NavigationStack, NavigationSplitView, programmatic navigation, deep linking

**Core Swift (1)**
- `swift-language` — Swift 6.2 features, macros, result builders, property wrappers

**App Experience Frameworks (3)**
- `alarmkit` — AlarmKit alarms and countdown timers, Live Activity integration, AlarmAttributes, AlarmButton
- `app-clips` — App Clip experiences, invocation, size limits, shared data
- `photos-camera-media` — PhotosPicker, AVCaptureSession, photo library, video recording, media permissions

**Data & Service Frameworks (7)**
- `cloudkit-sync` — CKContainer, CKRecord, subscriptions, sharing, NSPersistentCloudKitContainer
- `contacts-framework` — CNContactStore, fetch requests, key descriptors, CNContactPickerViewController, save requests
- `eventkit-calendar` — EKEventStore, EKEvent, EKReminder, recurrence rules, EventKitUI editors and choosers
- `healthkit` — HKHealthStore, queries, statistics, workout sessions, background delivery
- `musickit-audio` — MusicKit authorization, catalog search, ApplicationMusicPlayer, MPRemoteCommandCenter
- `passkit-wallet` — Apple Pay, PKPaymentRequest, PKPaymentAuthorizationController, Wallet passes
- `weatherkit` — WeatherService, current/hourly/daily forecasts, alerts, attribution requirements

**AI & Machine Learning (3)**
- `coreml` — Core ML model loading, prediction, MLTensor, compute unit configuration, VNCoreMLRequest, MLComputePlan
- `natural-language` — NLTokenizer, NLTagger, sentiment analysis, language identification, embeddings, Translation
- `speech-recognition` — SFSpeechRecognizer, on-device recognition, audio buffer processing

**iOS Engineering (5)**
- `authentication` — Sign in with Apple, ASAuthorizationController, passkeys, biometric auth (LAContext), credential management
- `background-processing` — BGTaskScheduler, background refresh, URLSession background transfers
- `device-integrity` — DeviceCheck (DCDevice per-device bits), App Attest (DCAppAttestService attestation and assertion flows)
- `metrickit-diagnostics` — MXMetricManager, hang diagnostics, crash reports, power metrics
- `ios-localization` — String Catalogs, pluralization, FormatStyle, right-to-left layout

**Hardware & Device Integration (4)**
- `core-motion` — CMMotionManager, CMPedometer, accelerometer, gyroscope, activity recognition, altitude
- `core-nfc` — NFCNDEFReaderSession, NFCTagReaderSession, NDEF reading/writing, background tag reading
- `pencilkit-drawing` — PKCanvasView, PKDrawing, PKToolPicker, Apple Pencil, PaperKit integration
- `realitykit-ar` — RealityView, entities, anchors, ARKit world tracking, raycasting, scene understanding

**Platform Integration (7)**
- `callkit-voip` — CXProvider, CXCallController, PushKit VoIP registration, call directory extensions
- `energykit` — ElectricityGuidance, EnergyVenue, grid forecasts, load event submission, electricity insights
- `homekit-matter` — HMHomeManager, accessories, rooms, actions, triggers, MatterSupport commissioning
- `mapkit-location` — MapKit, CoreLocation, annotations, geocoding, directions, geofencing
- `permissionkit` — AskCenter, PermissionQuestion, child communication safety, CommunicationLimits
- `shareplay-activities` — GroupActivity, GroupSession, GroupSessionMessenger, coordinated media playback
- `apple-on-device-ai` — Foundation Models framework, Core ML, MLX Swift, on-device LLM inference

### Skill refactors

- **swiftui-patterns** split into `swiftui-patterns`, `swiftui-navigation`, and `swiftui-layout-components` — each is now self-contained with no cross-references.
- **ios-security** split into `ios-security`, `authentication`, and `device-integrity` — each owns a clear domain boundary. `ios-security` covers Keychain/CryptoKit/data protection. `authentication` covers Sign in with Apple, passkeys, and biometric sign-in. `device-integrity` covers DeviceCheck and App Attest.
- All skills now self-contained with 4 or fewer reference files. No skill references another skill's files.

### Bundle restructure

v1.x had 6 themed bundles + 1 all-skills bundle. v2.0 has 8 themed bundles + 1 all-skills bundle.

Changes:
- `ios-framework-skills` (17 skills) split into `ios-app-framework-skills` (10) and `ios-data-framework-skills` (7).
- New `ios-ai-ml-skills` bundle created with `apple-on-device-ai`, `coreml`, `natural-language`, `speech-recognition`, `vision-framework`.
- AI/ML skills removed from `ios-engineering-skills` and `ios-platform-skills`.
- `ios-platform-skills` trimmed to 5 specialized platform integrations (HomeKit, SharePlay, CallKit, PermissionKit, EnergyKit).
- `ios-engineering-skills` refocused on 10 core engineering skills (networking, security, auth, accessibility, localization, debugging, diagnostics, background processing, device integrity, App Store review).

### Metadata improvements

- All 56 skill descriptions aligned with Agent Skills best practices.
- Bundle descriptions shortened and focused on user intent.
- Missing keywords added for major frameworks (Sendable, async-await, Foundation Models, BLE, Matter, etc.).
- All iOS 26 API claims verified against Apple documentation.

### Beta framework caveats

Three skills reference iOS 26 beta-only frameworks that may change before GM:
- `permissionkit` — PermissionKit (AskCenter, PermissionQuestion, CommunicationLimits)
- `energykit` — EnergyKit (ElectricityGuidance, EnergyVenue)
- `pencilkit-drawing` — references PaperKit integration

### Migration notes

- **Bundle name change**: `ios-framework-skills` no longer exists. Reinstall as `ios-app-framework-skills` and/or `ios-data-framework-skills`.
- **Skill file paths changed**: `swiftui-patterns/references/` files were reorganized during the split into three skills. Tools or scripts referencing old paths will need updating.
- **No breaking API changes**: All skills remain independently installable via `npx skills add` or `/plugin install`.

## v1.1.0

- Remove apple-docs MCP server references from skills.
- Fix npx skills CLI install commands in README.
- Bump plugin versions to 1.1.0.

## v1.0.0

- Initial release with 23 iOS and Swift development skills.
- 6 themed Claude Code plugin bundles + 1 all-skills bundle.
