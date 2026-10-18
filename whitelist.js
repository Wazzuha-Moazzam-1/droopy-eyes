const WHITELISTED_DOMAINS = new Set([
  "localhost",
  "github.com",
  "learn.microsoft.com",
  "stackoverflow.com"
]);
// side quest but i made an extension? lol    day2 
function isWhitelisted(rawUrl) {
  try {
    const url = new URL(rawUrl);

    // Do not interfere with browser-internal pages.
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return true;
    }

    const hostname = url.hostname.toLowerCase();

    return [...WHITELISTED_DOMAINS].some((allowedDomain) => {
      return (
        hostname === allowedDomain ||
        hostname.endsWith(`.${allowedDomain}`)
      );
    });
  } catch {
    // Avoid closing a tab if its URL cannot be interpreted safely.
    return true;
  }
}

async function inspectTab(tabId, changeInfo, tab) {
  const currentUrl = changeInfo.url ?? tab.url;

  if (!currentUrl) {
    return;
  }

  if (!isWhitelisted(currentUrl)) {
    console.log(`Closing non-whitelisted tab: ${currentUrl}`);

    try {
      await chrome.tabs.remove(tabId);
    } catch (error) {
      console.error(`Could not close tab ${tabId}:`, error);
    }
  }
}

chrome.tabs.onUpdated.addListener(inspectTab);