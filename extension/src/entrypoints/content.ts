import * as rrweb from "rrweb";
import { EventType, IncrementalSource } from "@rrweb/types";
import { VoiceProcessor } from '../voice/voice_processor';
import { VoiceRecorder } from "@/voice/voice_recorder";

let stopRecording: (() => void) | undefined = undefined;
let isRecordingActive = true;
let scrollTimeout: ReturnType<typeof setTimeout> | null = null;
let lastScrollY: number | null = null;
let lastDirection: "up" | "down" | null = null;
const DEBOUNCE_MS = 500;

let voiceProcessor: VoiceProcessor | null = null;
let isVoiceEnabled: boolean = false;

// --- Helper function to generate XPath ---
function getXPath(element: HTMLElement): string {
  if (element.id !== "") {
    return `id("${element.id}")`;
  }
  if (element === document.body) {
    return element.tagName.toLowerCase();
  }

  let ix = 0;
  const siblings = element.parentNode?.children;
  if (siblings) {
    for (let i = 0; i < siblings.length; i++) {
      const sibling = siblings[i];
      if (sibling === element) {
        return `${getXPath(
          element.parentElement as HTMLElement
        )}/${element.tagName.toLowerCase()}[${ix + 1}]`;
      }
      if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
        ix++;
      }
    }
  }
  // Fallback (should not happen often)
  return element.tagName.toLowerCase();
}
// --- End Helper ---

// --- Helper function to generate CSS Selector ---
// Expanded set of safe attributes (similar to Python)
const SAFE_ATTRIBUTES = new Set([
  "id",
  "name",
  "type",
  "placeholder",
  "aria-label",
  "aria-labelledby",
  "aria-describedby",
  "role",
  "for",
  "autocomplete",
  "required",
  "readonly",
  "alt",
  "title",
  "src",
  "href",
  "target",
  // Add common data attributes if stable
  "data-id",
  "data-qa",
  "data-cy",
  "data-testid",
]);

function getEnhancedCSSSelector(element: HTMLElement, xpath: string): string {
  try {
    // Base selector from simplified XPath or just tagName
    let cssSelector = element.tagName.toLowerCase();

    // Handle class attributes
    if (element.classList && element.classList.length > 0) {
      const validClassPattern = /^[a-zA-Z_][a-zA-Z0-9_-]*$/;
      element.classList.forEach((className) => {
        if (className && validClassPattern.test(className)) {
          cssSelector += `.${CSS.escape(className)}`;
        }
      });
    }

    // Handle other safe attributes
    for (const attr of element.attributes) {
      const attrName = attr.name;
      const attrValue = attr.value;

      if (attrName === "class") continue;
      if (!attrName.trim()) continue;
      if (!SAFE_ATTRIBUTES.has(attrName)) continue;

      const safeAttribute = CSS.escape(attrName);

      if (attrValue === "") {
        cssSelector += `[${safeAttribute}]`;
      } else {
        const safeValue = attrValue.replace(/"/g, '"');
        if (/["'<>`\s]/.test(attrValue)) {
          cssSelector += `[${safeAttribute}*="${safeValue}"]`;
        } else {
          cssSelector += `[${safeAttribute}="${safeValue}"]`;
        }
      }
    }
    return cssSelector;
  } catch (error) {
    console.error("Error generating enhanced CSS selector:", error);
    return `${element.tagName.toLowerCase()}[xpath="${xpath.replace(
      /"/g,
      '"'
    )}"]`;
  }
}

function createVoiceControlPanel(): void {
  // 检查是否已存在控制面板
  if (document.getElementById('voice-control-panel')) {
    return;
  }

  const panel = document.createElement('div');
  panel.id = 'voice-control-panel';
  panel.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 2147483647;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 16px;
    padding: 16px 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: all 0.3s ease;
    min-width: 200px;
  `;

  // 录音状态指示器
  const recordingIndicator = document.createElement('div');
  recordingIndicator.id = 'recording-indicator';
  recordingIndicator.style.cssText = `
    position: relative;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #9CA3AF;
    transition: all 0.3s ease;
  `;

  // 创建同心圆动画元素
  const pulseRing = document.createElement('div');
  pulseRing.id = 'pulse-ring';
  pulseRing.style.cssText = `
    position: absolute;
    top: -4px;
    left: -4px;
    width: 20px;
    height: 20px;
    border: 2px solid #EF4444;
    border-radius: 50%;
    opacity: 0;
    transform: scale(0.8);
    animation: none;
  `;

  recordingIndicator.appendChild(pulseRing);

  const voiceToggle = document.createElement('button');
  voiceToggle.textContent = '🎤 智能语音助理';
  voiceToggle.style.cssText = `
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 500;
    font-size: 13px;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
    flex: 1;
  `;

  // 添加按钮悬停效果
  voiceToggle.addEventListener('mouseenter', () => {
    voiceToggle.style.transform = 'translateY(-1px)';
    voiceToggle.style.boxShadow = '0 4px 12px rgba(79, 70, 229, 0.4)';
  });

  voiceToggle.addEventListener('mouseleave', () => {
    voiceToggle.style.transform = 'translateY(0)';
    voiceToggle.style.boxShadow = '0 2px 8px rgba(79, 70, 229, 0.3)';
  });

  voiceToggle.onclick = toggleVoiceRecording;

  const status = document.createElement('span');
  status.id = 'voice-status';
  status.textContent = '未启用';
  status.style.cssText = `
    color: #6B7280;
    font-size: 12px;
    font-weight: 500;
    min-width: 60px;
  `;

  // 添加CSS动画样式到页面
  if (!document.getElementById('voice-panel-styles')) {
    const style = document.createElement('style');
    style.id = 'voice-panel-styles';
    style.textContent = `
      @keyframes pulse-ring {
        0% {
          transform: scale(0.8);
          opacity: 1;
        }
        50% {
          transform: scale(1.2);
          opacity: 0.7;
        }
        100% {
          transform: scale(1.4);
          opacity: 0;
        }
      }
      
      @keyframes pulse-dot {
        0%, 100% {
          transform: scale(1);
          opacity: 1;
        }
        50% {
          transform: scale(1.1);
          opacity: 0.8;
        }
      }
      
      .recording-active {
        background: #EF4444 !important;
        animation: pulse-dot 1.5s ease-in-out infinite !important;
      }
      
      .pulse-ring-active {
        animation: pulse-ring 1.5s ease-out infinite !important;
        opacity: 1 !important;
      }
    `;
    document.head.appendChild(style);
  }

  panel.appendChild(recordingIndicator);
  panel.appendChild(voiceToggle);
  panel.appendChild(status);
  document.body.appendChild(panel);
}

async function initializeVoiceProcessor() {
  if (voiceProcessor) {
    console.log("Voice processor already initialized");
    return voiceProcessor;
  }

  try {
    console.log("正在尝试连接 WebSocket 并初始化处理器...");
    
    voiceProcessor = await VoiceProcessor.create('ws://127.0.0.1:8765/voice-stream');
    
    console.log("✅ WebSocket 连接成功，处理器准备就绪！");
    return voiceProcessor;

  } catch (error) {
    console.error("❌ 初始化语音处理器失败:", error);
    throw error;
  }
}

async function toggleVoiceRecording(): Promise<void> {
  const statusElement = document.getElementById('voice-status');
  const toggleButton = document.querySelector('#voice-control-panel button') as HTMLButtonElement;
  const recordingIndicator = document.getElementById('recording-indicator');
  const pulseRing = document.getElementById('pulse-ring');

  try {
    // Initialize voice processor only when needed
    if (!voiceProcessor) {
      if (statusElement) statusElement.textContent = '连接中...';
      if (recordingIndicator) {
        recordingIndicator.style.background = '#F59E0B';
      }
      await initializeVoiceProcessor();
    }

    if (!isVoiceEnabled) {
      await voiceProcessor!.startRecording();
      isVoiceEnabled = true;
      
      // 更新UI为录音状态
      if (toggleButton) {
        toggleButton.textContent = '🎤 语音增强 (开启)';
        toggleButton.style.background = 'linear-gradient(135deg, #EF4444, #DC2626)';
      }
      if (statusElement) {
        statusElement.textContent = '已启用';
        statusElement.style.color = '#10B981';
      }
      if (recordingIndicator) {
        recordingIndicator.classList.add('recording-active');
      }
      if (pulseRing) {
        pulseRing.classList.add('pulse-ring-active');
      }
    } else {
      await voiceProcessor!.stopRecording();
      isVoiceEnabled = false;
      
      // 更新UI为停止状态
      if (toggleButton) {
        toggleButton.textContent = '🎤 语音增强 (关闭)';
        toggleButton.style.background = 'linear-gradient(135deg, #4F46E5, #7C3AED)';
      }
      if (statusElement) {
        statusElement.textContent = '已关闭';
        statusElement.style.color = '#6B7280';
      }
      if (recordingIndicator) {
        recordingIndicator.classList.remove('recording-active');
        recordingIndicator.style.background = '#9CA3AF';
      }
      if (pulseRing) {
        pulseRing.classList.remove('pulse-ring-active');
      }
    }
  } catch (error) {
    console.error('语音录制切换失败:', error);
    
    // 错误状态UI
    if (statusElement) {
      statusElement.textContent = '连接失败';
      statusElement.style.color = '#EF4444';
    }
    if (recordingIndicator) {
      recordingIndicator.style.background = '#EF4444';
      recordingIndicator.classList.remove('recording-active');
    }
    if (pulseRing) {
      pulseRing.classList.remove('pulse-ring-active');
    }
    
    let errorMessage = '未知错误';
    if (error && typeof error === 'object' && 'message' in error) {
      errorMessage = (error as { message: string }).message;
    }
    alert(`语音功能错误: ${errorMessage}`);
  }
}

function startRecorder() {
  if (stopRecording) {
    console.log("Recorder already running.");
    return; // Already running
  }
  console.log("Starting rrweb recorder for:", window.location.href);
  isRecordingActive = true;

  createVoiceControlPanel();
  
  stopRecording = rrweb.record({
    emit(event) {
      if (!isRecordingActive) return;
      const enhancedEvent = {
        ...event,
        timestamp: Date.now() / 1000  // 添加精确的时间戳
      };


      // Handle scroll events with debouncing and direction detection
      if (
        event.type === EventType.IncrementalSnapshot &&
        event.data.source === IncrementalSource.Scroll
      ) {
        const scrollData = event.data as { id: number; x: number; y: number };
        const currentScrollY = scrollData.y;

        // Round coordinates
        const roundedScrollData = {
          ...scrollData,
          x: Math.round(scrollData.x),
          y: Math.round(scrollData.y),
        };

        // Determine scroll direction
        let currentDirection: "up" | "down" | null = null;
        if (lastScrollY !== null) {
          currentDirection = currentScrollY > lastScrollY ? "down" : "up";
        }

        // Record immediately if direction changes
        if (
          lastDirection !== null &&
          currentDirection !== null &&
          currentDirection !== lastDirection
        ) {
          if (scrollTimeout) {
            clearTimeout(scrollTimeout);
            scrollTimeout = null;
          }
          chrome.runtime.sendMessage({
            type: "RRWEB_EVENT",
            payload: {
              ...enhancedEvent,
              data: roundedScrollData, // Use rounded coordinates
            },
          });
          lastDirection = currentDirection;
          lastScrollY = currentScrollY;
          return;
        }

        // Update direction and position
        lastDirection = currentDirection;
        lastScrollY = currentScrollY;

        // Debouncer
        if (scrollTimeout) {
          clearTimeout(scrollTimeout);
        }
        scrollTimeout = setTimeout(() => {
          chrome.runtime.sendMessage({
            type: "RRWEB_EVENT",
            payload: {
              ...enhancedEvent,
              data: roundedScrollData, // Use rounded coordinates
            },
          });
          scrollTimeout = null;
          lastDirection = null; // Reset direction for next scroll
        }, DEBOUNCE_MS);
      } else {
        // Pass through non-scroll events unchanged
        chrome.runtime.sendMessage({ type: "RRWEB_EVENT", payload: enhancedEvent });
      }
    },
    maskInputOptions: {
      password: true,
    },
    checkoutEveryNms: 10000,
    checkoutEveryNth: 200,
  });

  // Add the stop function to window for potenti
  // --- End CSS Selector Helper --- al manual cleanup
  (window as any).rrwebStop = stopRecorder;

  // --- Attach Custom Event Listeners Permanently ---
  // These listeners are always active, but the handlers check `isRecordingActive`
  document.addEventListener("click", handleCustomClick, true);
  document.addEventListener("input", handleInput, true);
  document.addEventListener("change", handleSelectChange, true);
  document.addEventListener("keydown", handleKeydown, true);
  document.addEventListener("mouseover", handleMouseOver, true);
  document.addEventListener("mouseout", handleMouseOut, true);
  document.addEventListener("focus", handleFocus, true);
  document.addEventListener("blur", handleBlur, true);
  console.log("Permanently attached custom event listeners.");
}

function stopRecorder() {
  if (stopRecording) {
    console.log("Stopping rrweb recorder for:", window.location.href);
    stopRecording();
    stopRecording = undefined;
    isRecordingActive = false;

    if (voiceProcessor) {
      voiceProcessor.dispose();
      voiceProcessor = null;
    }
    isVoiceEnabled = false;
    
    const panel = document.getElementById('voice-control-panel');
    if (panel) {
      panel.remove();
    }

    (window as any).rrwebStop = undefined; // Clean up window property
    // Remove custom listeners when recording stops
    document.removeEventListener("click", handleCustomClick, true);
    document.removeEventListener("input", handleInput, true);
    document.removeEventListener("change", handleSelectChange, true); // Remove change listener
    document.removeEventListener("keydown", handleKeydown, true); // Remove keydown listener
    document.removeEventListener("mouseover", handleMouseOver, true);
    document.removeEventListener("mouseout", handleMouseOut, true);
    document.removeEventListener("focus", handleFocus, true);
    document.removeEventListener("blur", handleBlur, true);
  } else {
    console.log("Recorder not running, cannot stop.");
  }
}

// --- Custom Click Handler ---
function handleCustomClick(event: MouseEvent) {
  if (!isRecordingActive) return;
  const targetElement = event.target as HTMLElement;
  if (!targetElement) return;

  try {
    const xpath = getXPath(targetElement);
    const clickData = {
      timestamp: Date.now() / 1000, // Use seconds for rrweb compatibility
      url: document.location.href, // Use document.location for main page URL
      frameUrl: window.location.href, // URL of the frame where the event occurred
      xpath: xpath,
      cssSelector: getEnhancedCSSSelector(targetElement, xpath),
      elementTag: targetElement.tagName,
      elementText: targetElement.textContent?.trim().slice(0, 200) || "",
    };
    console.log("Sending CUSTOM_CLICK_EVENT:", clickData);
    chrome.runtime.sendMessage({
      type: "CUSTOM_CLICK_EVENT",
      payload: clickData,
    });
  } catch (error) {
    console.error("Error capturing click data:", error);
  }
}
// --- End Custom Click Handler ---

// --- Custom Input Handler ---
function handleInput(event: Event) {
  if (!isRecordingActive) return;
  const targetElement = event.target as HTMLInputElement | HTMLTextAreaElement;
  if (!targetElement || !("value" in targetElement)) return;
  const isPassword = targetElement.type === "password";

  try {
    const xpath = getXPath(targetElement);
    const inputData = {
      timestamp: Date.now() / 1000,
      url: document.location.href,
      frameUrl: window.location.href,
      xpath: xpath,
      cssSelector: getEnhancedCSSSelector(targetElement, xpath),
      elementTag: targetElement.tagName,
      value: isPassword ? "********" : targetElement.value,
    };
    console.log("Sending CUSTOM_INPUT_EVENT:", inputData);
    chrome.runtime.sendMessage({
      type: "CUSTOM_INPUT_EVENT",
      payload: inputData,
    });
  } catch (error) {
    console.error("Error capturing input data:", error);
  }
}
// --- End Custom Input Handler ---

// 处理来自语音处理器的消息
function handleVoiceInput(event: MessageEvent) {
  if (event.data.type === 'VOICE_INPUT') {
    console.log('收到语音输入:', event.data);
    
    // 转发到后台脚本进行处理
    chrome.runtime.sendMessage({
      type: "VOICE_INPUT_EVENT",
      payload: {
        text: event.data.text,
        timestamp: event.data.timestamp,
        url: window.location.href
      }
    });
  }
}

// --- Custom Select Change Handler ---
function handleSelectChange(event: Event) {
  if (!isRecordingActive) return;
  const targetElement = event.target as HTMLSelectElement;
  // Ensure it's a select element
  if (!targetElement || targetElement.tagName !== "SELECT") return;

  try {
    const xpath = getXPath(targetElement);
    const selectedOption = targetElement.options[targetElement.selectedIndex];
    const selectData = {
      timestamp: Date.now(),
      url: document.location.href,
      frameUrl: window.location.href,
      xpath: xpath,
      cssSelector: getEnhancedCSSSelector(targetElement, xpath),
      elementTag: targetElement.tagName,
      selectedValue: targetElement.value,
      selectedText: selectedOption ? selectedOption.text : "", // Get selected option text
    };
    console.log("Sending CUSTOM_SELECT_EVENT:", selectData);
    chrome.runtime.sendMessage({
      type: "CUSTOM_SELECT_EVENT",
      payload: selectData,
    });
  } catch (error) {
    console.error("Error capturing select change data:", error);
  }
}
// --- End Custom Select Change Handler ---

// --- Custom Keydown Handler ---
// Set of keys we want to capture explicitly
const CAPTURED_KEYS = new Set([
  "Enter",
  "Tab",
  "Escape",
  "ArrowUp",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "Home",
  "End",
  "PageUp",
  "PageDown",
  "Backspace",
  "Delete",
]);

function handleKeydown(event: KeyboardEvent) {
  if (!isRecordingActive) return;

  const key = event.key;
  let keyToLog = "";

  // Check if it's a key we explicitly capture
  if (CAPTURED_KEYS.has(key)) {
    keyToLog = key;
  }
  // Check for common modifier combinations (Ctrl/Cmd + key)
  else if (
    (event.ctrlKey || event.metaKey) &&
    key.length === 1 &&
    /[a-zA-Z0-9]/.test(key)
  ) {
    // Use 'CmdOrCtrl' to be cross-platform friendly in logs
    keyToLog = `CmdOrCtrl+${key.toUpperCase()}`;
  }
  // You could add more specific checks here (Alt+, Shift+, etc.) if needed

  // If we have a key we want to log, send the event
  if (keyToLog) {
    const targetElement = event.target as HTMLElement;
    let xpath = "";
    let cssSelector = "";
    let elementTag = "document"; // Default if target is not an element
    if (targetElement && typeof targetElement.tagName === "string") {
      try {
        xpath = getXPath(targetElement);
        cssSelector = getEnhancedCSSSelector(targetElement, xpath);
        elementTag = targetElement.tagName;
      } catch (e) {
        console.error("Error getting selector for keydown target:", e);
      }
    }

    try {
      const keyData = {
        timestamp: Date.now(),
        url: document.location.href,
        frameUrl: window.location.href,
        key: keyToLog, // The key or combination pressed
        xpath: xpath, // XPath of the element in focus (if any)
        cssSelector: cssSelector, // CSS selector of the element in focus (if any)
        elementTag: elementTag, // Tag name of the element in focus
      };
      console.log("Sending CUSTOM_KEY_EVENT:", keyData);
      chrome.runtime.sendMessage({
        type: "CUSTOM_KEY_EVENT",
        payload: keyData,
      });
    } catch (error) {
      console.error("Error capturing keydown data:", error);
    }
  }
}
// --- End Custom Keydown Handler ---

// Store the current overlay to manage its lifecycle
let currentOverlay: HTMLDivElement | null = null;
let currentFocusOverlay: HTMLDivElement | null = null;

// Handle mouseover to create overlay
function handleMouseOver(event: MouseEvent) {
  if (!isRecordingActive) return;
  const targetElement = event.target as HTMLElement;
  if (!targetElement) return;

  // Remove any existing overlay to avoid duplicates
  if (currentOverlay) {
    // console.log('Removing existing overlay');
    currentOverlay.remove();
    currentOverlay = null;
  }

  try {
    const xpath = getXPath(targetElement);
    // console.log('XPath of target element:', xpath);
    let elementToHighlight: HTMLElement | null = document.evaluate(
      xpath,
      document,
      null,
      XPathResult.FIRST_ORDERED_NODE_TYPE,
      null
    ).singleNodeValue as HTMLElement | null;
    if (!elementToHighlight) {
      const enhancedSelector = getEnhancedCSSSelector(targetElement, xpath);
      console.log("CSS Selector:", enhancedSelector);
      const elements = document.querySelectorAll<HTMLElement>(enhancedSelector);

      // Try to find the element under the mouse
      for (const el of elements) {
        const rect = el.getBoundingClientRect();
        if (
          event.clientX >= rect.left &&
          event.clientX <= rect.right &&
          event.clientY >= rect.top &&
          event.clientY <= rect.bottom
        ) {
          elementToHighlight = el;
          break;
        }
      }
    }
    if (elementToHighlight) {
      const rect = elementToHighlight.getBoundingClientRect();
      const highlightOverlay = document.createElement("div");
      highlightOverlay.className = "highlight-overlay";
      Object.assign(highlightOverlay.style, {
        position: "absolute",
        top: `${rect.top + window.scrollY}px`,
        left: `${rect.left + window.scrollX}px`,
        width: `${rect.width}px`,
        height: `${rect.height}px`,
        border: "2px solid lightgreen",
        backgroundColor: "rgba(144, 238, 144, 0.05)", // lightgreen tint
        pointerEvents: "none",
        zIndex: "2147483000",
      });
      document.body.appendChild(highlightOverlay);
      currentOverlay = highlightOverlay;
    } else {
      console.warn("No element found to highlight for xpath:", xpath);
    }
  } catch (error) {
    console.error("Error creating highlight overlay:", error);
  }
}

// Handle mouseout to remove overlay
function handleMouseOut(event: MouseEvent) {
  if (!isRecordingActive) return;
  if (currentOverlay) {
    currentOverlay.remove();
    currentOverlay = null;
  }
}

// Handle focus to create red overlay for input elements
function handleFocus(event: FocusEvent) {
  if (!isRecordingActive) return;
  const targetElement = event.target as HTMLElement;
  if (
    !targetElement ||
    !["INPUT", "TEXTAREA", "SELECT"].includes(targetElement.tagName)
  )
    return;

  // Remove any existing focus overlay to avoid duplicates
  if (currentFocusOverlay) {
    currentFocusOverlay.remove();
    currentFocusOverlay = null;
  }

  try {
    const xpath = getXPath(targetElement);
    let elementToHighlight: HTMLElement | null = document.evaluate(
      xpath,
      document,
      null,
      XPathResult.FIRST_ORDERED_NODE_TYPE,
      null
    ).singleNodeValue as HTMLElement | null;
    if (!elementToHighlight) {
      const enhancedSelector = getEnhancedCSSSelector(targetElement, xpath);
      elementToHighlight = document.querySelector(enhancedSelector);
    }
    if (elementToHighlight) {
      const rect = elementToHighlight.getBoundingClientRect();
      const focusOverlay = document.createElement("div");
      focusOverlay.className = "focus-overlay";
      Object.assign(focusOverlay.style, {
        position: "absolute",
        top: `${rect.top + window.scrollY}px`,
        left: `${rect.left + window.scrollX}px`,
        width: `${rect.width}px`,
        height: `${rect.height}px`,
        border: "2px solid red",
        backgroundColor: "rgba(255, 0, 0, 0.05)", // Red tint
        pointerEvents: "none",
        zIndex: "2147483100", // Higher than mouseover overlay (2147483000)
      });
      document.body.appendChild(focusOverlay);
      currentFocusOverlay = focusOverlay;
    } else {
      console.warn("No element found to highlight for focus, xpath:", xpath);
    }
  } catch (error) {
    console.error("Error creating focus overlay:", error);
  }
}

// Handle blur to remove focus overlay
function handleBlur(event: FocusEvent) {
  if (!isRecordingActive) return;
  if (currentFocusOverlay) {
    currentFocusOverlay.remove();
    currentFocusOverlay = null;
  }
}

export default defineContentScript({
  matches: ["<all_urls>"],
  main(ctx) {
    window.addEventListener('message', handleVoiceInput);
    // Listener for status updates from the background script
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.type === "SET_RECORDING_STATUS") {
        const shouldBeRecording = message.payload;
        console.log(`Received recording status update: ${shouldBeRecording}`);
        if (shouldBeRecording && !isRecordingActive) {
          startRecorder();
        } else if (!shouldBeRecording && isRecordingActive) {
          stopRecorder();
        }
      }
      // If needed, handle other message types here
    });

    // Request initial status when the script loads
    console.log(
      "Content script loaded, requesting initial recording status..."
    );
    chrome.runtime.sendMessage(
      { type: "REQUEST_RECORDING_STATUS" },
      (response) => {
        if (chrome.runtime.lastError) {
          console.error(
            "Error requesting initial status:",
            chrome.runtime.lastError.message
          );
          // Handle error - maybe default to not recording?
          return;
        }
        if (response && response.isRecordingEnabled) {
          console.log("Initial status: Recording enabled.");
          startRecorder();
        } else {
          console.log("Initial status: Recording disabled.");
          // Ensure recorder is stopped if it somehow started
          stopRecorder();
        }
      }
    );

    // Optional: Clean up recorder if the page is unloading
    window.addEventListener("beforeunload", () => {
      if (voiceProcessor) {
        voiceProcessor.dispose();
      }
      window.removeEventListener('message', handleVoiceInput);

      // Also remove permanent listeners on unload?
      // Might not be strictly necessary as the page context is destroyed,
      // but good practice if the script could somehow persist.
      document.removeEventListener("click", handleCustomClick, true);
      document.removeEventListener("input", handleInput, true);
      document.removeEventListener("change", handleSelectChange, true);
      document.removeEventListener("keydown", handleKeydown, true);
      document.removeEventListener("mouseover", handleMouseOver, true);
      document.removeEventListener("mouseout", handleMouseOut, true);
      document.removeEventListener("focus", handleFocus, true);
      document.removeEventListener("blur", handleBlur, true);
      stopRecorder(); // Ensure rrweb is stopped
    });

    // Optional: Log when the content script is injected
    // console.log("rrweb recorder injected into:", window.location.href);

    // Listener for potential messages from popup/background if needed later
    // chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    //   if (msg.type === 'GET_EVENTS') {
    //     sendResponse(events);
    //   }
    //   return true; // Keep the message channel open for asynchronous response
    // });
  },
});
