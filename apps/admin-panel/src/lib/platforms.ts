export const SUPPORTED_APP_PLATFORMS = Object.freeze(['macOS', 'windows', 'Linux'] as const);

export type SupportedAppPlatform = (typeof SUPPORTED_APP_PLATFORMS)[number];

export const toPlatformSlug = (platform: SupportedAppPlatform | string) => platform.toLowerCase();
