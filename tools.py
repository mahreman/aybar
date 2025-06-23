import json
import os
import logging
import re # For a robust _perform_internet_search within maps_or_search
from typing import Optional, List, Dict, Any, Tuple # Added Tuple
# from aybarcore import EnhancedAybar # This will cause circular dependency if tools are imported in aybarcore too soon.
# Use string literal for type hint or Any for now.
EnhancedAybarType = Any

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

FROM_AYBAR_FILE = "from_aybar.txt"

# --- Helper function to get logger from aybar_instance or default ---
def _get_tool_logger(aybar_instance: EnhancedAybarType):
    # A more robust way to get logger, falling back to module logger if aybar_instance has no logger
    if hasattr(aybar_instance, 'logger') and aybar_instance.logger is not None:
        return aybar_instance.logger
    return logger # Fallback to module-level logger

# --- Tool Functions ---

def maps_or_search(query: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Navigates to a URL if 'query' is a URL. Otherwise, performs an internet search for the 'query'.
    Uses aybar_instance's web_surfer_system for navigation and _perform_internet_search for searching.

    Args:
        query: The URL to navigate to or the search term.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process behind this action.

    Returns:
        A string describing the result of the action.
    @category: web_interaction
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'maps_or_search' called. Query: '{query}', Thought: '{thought}'")

    if not (hasattr(aybar_instance, 'web_surfer_system') and aybar_instance.web_surfer_system and \
            hasattr(aybar_instance.web_surfer_system, 'driver') and aybar_instance.web_surfer_system.driver):
        tool_logger.warning("Web surfer system is not available or not initialized.")
        return "Web surfer system is not available or not initialized."

    is_url = query.lower().startswith("http://") or query.lower().startswith("https://") or query.lower().startswith("www.")

    try:
        if is_url:
            tool_logger.info(f"Navigating to URL: {query}")
            aybar_instance.web_surfer_system.navigate_to(query)
            # Consider waiting for page load if navigate_to is not blocking
            # For now, assume navigation completes and page is ready for observation by Aybar
            return f"Navigated to URL: {query}. Aybar should now observe the page content."
        else:
            tool_logger.info(f"Performing internet search for: {query}")
            if not hasattr(aybar_instance, '_perform_internet_search'):
                tool_logger.error("'_perform_internet_search' method not found on aybar_instance.")
                return "Error: Internet search functionality is missing."
            search_summary = aybar_instance._perform_internet_search(query=query) # Call the method on the instance
            return f"Internet search performed for '{query}'. Summary: {search_summary}"
    except Exception as e:
        tool_logger.error(f"Error during maps_or_search for '{query}': {e}", exc_info=True)
        return f"Error during maps_or_search for '{query}': {e}"

def ask_user_via_file(question: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Asks a question to the user by writing it to 'from_aybar.txt'.
    The TelegramBridge is expected to pick this up.

    Args:
        question: The question to ask the user.
        aybar_instance: The EnhancedAybar instance (used for logging).
        thought: Optional. The thought process.

    Returns:
        A string confirming the action.
    @category: core_utils
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'ask_user_via_file' called. Question: '{question[:50]}...', Thought: '{thought}'")
    try:
        with open(FROM_AYBAR_FILE, "w", encoding="utf-8") as f:
            f.write(question)
        return f"Question for user ('{question[:50]}...') written to {FROM_AYBAR_FILE} for Telegram delivery."
    except Exception as e:
        tool_logger.error(f"Error writing question to {FROM_AYBAR_FILE}: {e}", exc_info=True)
        return f"Failed to write question to file for user: {e}"

def update_identity(aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Initiates Aybar's identity update process based on recent experiences.
    This calls an internal method on the Aybar instance.

    Args:
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string indicating the result of the identity update attempt.
    @category: cognitive_emotional
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'update_identity' called. Thought: '{thought}'")
    if hasattr(aybar_instance, '_update_identity') and callable(getattr(aybar_instance, '_update_identity')):
        try:
            return aybar_instance._update_identity()
        except Exception as e:
            tool_logger.error(f"Error during _update_identity: {e}", exc_info=True)
            return f"Error updating identity: {e}"
    else:
        tool_logger.warning("'_update_identity' method not found on aybar_instance.")
        return "Identity update mechanism is not available."

def finish_goal(summary: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Marks the current goal (main or sub-goal) as finished and cleans up goal state.

    Args:
        summary: A summary of how the goal was completed.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string confirming goal completion.
    @category: core_utils
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'finish_goal' called. Summary: '{summary}', Thought: '{thought}'")

    if not hasattr(aybar_instance, 'cognitive_system'):
        tool_logger.error("Cognitive system not found on aybar_instance for finish_goal.")
        return "Cognitive system not found on aybar_instance."
    if not hasattr(aybar_instance, 'current_turn'): # Check for current_turn as well
        tool_logger.error("current_turn not found on aybar_instance for finish_goal.")
        return "current_turn not found on aybar_instance for finish_goal."


    cognitive_system = aybar_instance.cognitive_system
    current_task = cognitive_system.get_current_task(aybar_instance.current_turn) # Get task before clearing

    if not current_task:
        return "No active goal to finish."

    response_message = f"Goal/Task '{current_task}' finished. Summary: {summary}"

    if cognitive_system.sub_goals and 0 <= cognitive_system.current_sub_goal_index < len(cognitive_system.sub_goals):
        completed_sub_goal = cognitive_system.sub_goals[cognitive_system.current_sub_goal_index]
        cognitive_system.current_sub_goal_index += 1
        tool_logger.info(f"Sub-goal '{completed_sub_goal}' marked as complete.")
        if 0 <= cognitive_system.current_sub_goal_index < len(cognitive_system.sub_goals):
            next_sub_goal = cognitive_system.sub_goals[cognitive_system.current_sub_goal_index]
            response_message += f" Moving to next sub-goal: '{next_sub_goal}'."
        else:
            tool_logger.info(f"All sub-goals for '{cognitive_system.main_goal}' completed.")
            response_message += f" All sub-goals for '{cognitive_system.main_goal}' completed."
            cognitive_system.clear_all_goals() # Clear all as main goal is also considered done
    else: # It was a main goal without sub-goals, or all sub-goals were already done
        tool_logger.info(f"Main goal '{cognitive_system.main_goal}' marked as complete.")
        cognitive_system.clear_all_goals()

    return response_message

def summarize_and_reset(aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Resets Aybar's current goal, typically used to break from a loop or confusion.
    The 'thought' should explain why the reset is needed.

    Args:
        aybar_instance: The EnhancedAybar instance.
        thought: Explanation for the reset.

    Returns:
        A string confirming the reset.
    @category: core_utils
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'summarize_and_reset' called. Thought: '{thought}'")

    if not hasattr(aybar_instance, 'cognitive_system'):
        tool_logger.error("Cognitive system not found on aybar_instance for summarize_and_reset.")
        return "Cognitive system not found on aybar_instance."

    aybar_instance.cognitive_system.clear_all_goals()
    return f"Current goals have been reset due to: '{thought}'. Aybar will now determine a new goal."

# --- Additional Tool Functions (from previous step) ---

def creative_generation(creation_type: str, theme: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Generates artistic content of a specified type and theme.
    This calls an internal method on the Aybar instance.

    Args:
        creation_type: The type of content to create (e.g., "text", "poem", "short_story").
        theme: The theme for the creative content.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string containing the generated creative content or an error/status message.
    @category: cognitive_emotional
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'creative_generation' called. Type: '{creation_type}', Theme: '{theme}', Thought: '{thought}'")
    if hasattr(aybar_instance, '_creative_generation') and callable(getattr(aybar_instance, '_creative_generation')):
        try:
            return aybar_instance._creative_generation(creation_type=creation_type, theme=theme)
        except Exception as e:
            tool_logger.error(f"Error during _creative_generation: {e}", exc_info=True)
            return f"Error during creative generation: {e}"
    else:
        tool_logger.warning("'_creative_generation' method not found on aybar_instance.")
        return "Creative generation mechanism is not available."

def regulate_emotion(strategy: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Initiates a conscious action to balance Aybar's emotional state using a specified strategy.
    This calls an internal method on the Aybar instance.

    Args:
        strategy: The emotional regulation strategy to use (e.g., "calm_monologue", "focus_on_sensory_input").
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string indicating the result of the emotion regulation attempt.
    @category: cognitive_emotional
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'regulate_emotion' called. Strategy: '{strategy}', Thought: '{thought}'")
    if hasattr(aybar_instance, '_regulate_emotion') and callable(getattr(aybar_instance, '_regulate_emotion')):
        try:
            return aybar_instance._regulate_emotion(strategy=strategy)
        except Exception as e:
            tool_logger.error(f"Error during _regulate_emotion: {e}", exc_info=True)
            return f"Error during emotion regulation: {e}"
    else:
        tool_logger.warning("'_regulate_emotion' method not found on aybar_instance.")
        return "Emotion regulation mechanism is not available."

def analyze_memory(query: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Analyzes Aybar's own episodic memory to find patterns or answer a specific query about its past.
    This calls an internal method on the Aybar instance.

    Args:
        query: The query or question about Aybar's memory.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string containing the insight or result from memory analysis.
    @category: cognitive_emotional
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'analyze_memory' called. Query: '{query}', Thought: '{thought}'")
    if hasattr(aybar_instance, '_analyze_memory') and callable(getattr(aybar_instance, '_analyze_memory')):
        try:
            return aybar_instance._analyze_memory(query=query)
        except Exception as e:
            tool_logger.error(f"Error during _analyze_memory: {e}", exc_info=True)
            return f"Error during memory analysis: {e}"
    else:
        tool_logger.warning("'_analyze_memory' method not found on aybar_instance.")
        return "Memory analysis mechanism is not available."

def run_internal_simulation(scenario: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Runs an internal mental simulation based on a given scenario.
    This calls an internal method on the Aybar instance.

    Args:
        scenario: The scenario to simulate.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string containing the result or output of the internal simulation.
    @category: cognitive_emotional
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'run_internal_simulation' called. Scenario: '{scenario[:50]}...', Thought: '{thought}'")
    if hasattr(aybar_instance, '_run_internal_simulation') and callable(getattr(aybar_instance, '_run_internal_simulation')):
        try:
            return aybar_instance._run_internal_simulation(scenario=scenario)
        except Exception as e:
            tool_logger.error(f"Error during _run_internal_simulation: {e}", exc_info=True)
            return f"Error during internal simulation: {e}"
    else:
        tool_logger.warning("'_run_internal_simulation' method not found on aybar_instance.")
        return "Internal simulation mechanism is not available."

def handle_interaction(user_id: str, goal: str, method: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Initiates a social interaction with a specified goal and method.
    This calls an internal method on the Aybar instance.

    Args:
        user_id: The ID of the user/entity to interact with.
        goal: The goal of the interaction (e.g., "build_trust", "increase_familiarity").
        method: The method of interaction (e.g., "ask_general_question").
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string representing Aybar's response or question in the interaction.
    @category: social_interaction
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'handle_interaction' called. User ID: {user_id}, Goal: {goal}, Method: {method}, Thought: {thought}")
    if hasattr(aybar_instance, '_handle_interaction') and callable(getattr(aybar_instance, '_handle_interaction')):
        try:
            return aybar_instance._handle_interaction(user_id=user_id, goal=goal, method=method)
        except Exception as e:
            tool_logger.error(f"Error during _handle_interaction: {e}", exc_info=True)
            return f"Error during interaction handling: {e}"
    else:
        tool_logger.warning("'_handle_interaction' method not found on aybar_instance.")
        return "Interaction handling mechanism is not available."

def perform_meta_reflection(turn_to_analyze: int, thought_to_analyze: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Analyzes and critiques a previous thought process from a specific turn.
    This calls an internal method on the Aybar instance.

    Args:
        turn_to_analyze: The turn number of the thought process to analyze.
        thought_to_analyze: The specific thought from that turn to reflect upon.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The current thought process behind performing this meta-reflection.

    Returns:
        A string containing the analysis or insights from the meta-reflection.
    @category: cognitive_emotional
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'perform_meta_reflection' called for turn {turn_to_analyze}. Thought: '{thought}'")
    if hasattr(aybar_instance, '_perform_meta_reflection') and callable(getattr(aybar_instance, '_perform_meta_reflection')):
        try:
            return aybar_instance._perform_meta_reflection(turn_to_analyze=turn_to_analyze, thought_to_analyze=thought_to_analyze)
        except Exception as e:
            tool_logger.error(f"Error during _perform_meta_reflection: {e}", exc_info=True)
            return f"Error during meta-reflection: {e}"
    else:
        tool_logger.warning("'_perform_meta_reflection' method not found on aybar_instance.")
        return "Meta-reflection mechanism is not available."


# --- Tools from ComputerControlSystem ---

def keyboard_type(text_to_type: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Types the given text using the computer's keyboard.
    This interacts with the ComputerControlSystem.

    Args:
        text_to_type: The text string to be typed.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string confirming the action or an error message.
    @category: system_interaction
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'keyboard_type' called. Text: '{text_to_type[:30]}...', Thought: '{thought}'")
    if hasattr(aybar_instance, 'computer_control_system') and aybar_instance.computer_control_system:
        try:
            return aybar_instance.computer_control_system.keyboard_type(text=text_to_type)
        except Exception as e:
            tool_logger.error(f"Error during keyboard_type: {e}", exc_info=True)
            return f"Error typing text: {e}"
    else:
        tool_logger.warning("'computer_control_system' not found on aybar_instance.")
        return "Keyboard control system is not available."

def mouse_click(aybar_instance: EnhancedAybarType, x: int, y: int, double_click: bool = False, thought: Optional[str] = None) -> str:
    """
    Performs a mouse click (or double click) at the specified screen coordinates.
    This interacts with the ComputerControlSystem.

    Args:
        x: The x-coordinate for the mouse click.
        y: The y-coordinate for the mouse click.
        double_click: Whether to perform a double click. Defaults to False.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string confirming the action or an error message.
    @category: system_interaction
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'mouse_click' called. Coordinates: ({x},{y}), DoubleClick: {double_click}, Thought: '{thought}'")
    if hasattr(aybar_instance, 'computer_control_system') and aybar_instance.computer_control_system:
        try:
            return aybar_instance.computer_control_system.mouse_click(x=x, y=y, double_click=double_click)
        except Exception as e:
            tool_logger.error(f"Error during mouse_click: {e}", exc_info=True)
            return f"Error performing mouse click: {e}"
    else:
        tool_logger.warning("'computer_control_system' not found on aybar_instance.")
        return "Mouse control system is not available."

def analyze_screen(question: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Captures the screen and uses a VLM (Vision Language Model) to answer a question about the screen content.
    This interacts with the ComputerControlSystem.

    Args:
        question: The question to ask about the screen content.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string containing the VLM's answer or an error message.
    @category: system_interaction
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'analyze_screen' called. Question: '{question}', Thought: '{thought}'")
    if hasattr(aybar_instance, 'computer_control_system') and aybar_instance.computer_control_system:
        try:
            # The analyze_screen_with_vlm in ComputerControlSystem handles capturing and VLM call
            return aybar_instance.computer_control_system.analyze_screen_with_vlm(question=question)
        except Exception as e:
            tool_logger.error(f"Error during analyze_screen: {e}", exc_info=True)
            return f"Error analyzing screen: {e}"
    else:
        tool_logger.warning("'computer_control_system' not found on aybar_instance.")
        return "Screen analysis system is not available."

# --- Tools from WebSurferSystem ---

def web_click(target_xpath: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Performs a click action on a web element identified by its XPath.
    This interacts with the WebSurferSystem.

    Args:
        target_xpath: The XPath of the element to click.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string describing the result of the click action.
    @category: web_interaction
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'web_click' called. XPath: '{target_xpath}', Thought: '{thought}'")
    if hasattr(aybar_instance, 'web_surfer_system') and aybar_instance.web_surfer_system and aybar_instance.web_surfer_system.driver:
        try:
            # The perform_web_action method in WebSurferSystem needs to be called with a dict
            action_item = {"action_type": "click", "target_xpath": target_xpath}
            return aybar_instance.web_surfer_system.perform_web_action(action_item)
        except Exception as e:
            tool_logger.error(f"Error during web_click: {e}", exc_info=True)
            return f"Error performing web click: {e}"
    else:
        tool_logger.warning("'web_surfer_system' not available or not initialized for web_click.")
        return "Web surfer system is not available for web_click."

def web_type(target_xpath: str, text_to_type: str, aybar_instance: EnhancedAybarType, thought: Optional[str] = None) -> str:
    """
    Types the given text into a web element identified by its XPath.
    This interacts with the WebSurferSystem.

    Args:
        target_xpath: The XPath of the input element.
        text_to_type: The text to type into the element.
        aybar_instance: The EnhancedAybar instance.
        thought: Optional. The thought process.

    Returns:
        A string describing the result of the type action.
    @category: web_interaction
    """
    tool_logger = _get_tool_logger(aybar_instance)
    tool_logger.info(f"Tool 'web_type' called. XPath: '{target_xpath}', Text: '{text_to_type[:30]}...', Thought: '{thought}'")
    if hasattr(aybar_instance, 'web_surfer_system') and aybar_instance.web_surfer_system and aybar_instance.web_surfer_system.driver:
        try:
            # The perform_web_action method in WebSurferSystem needs to be called with a dict
            action_item = {"action_type": "type", "target_xpath": target_xpath, "text": text_to_type}
            return aybar_instance.web_surfer_system.perform_web_action(action_item)
        except Exception as e:
            tool_logger.error(f"Error during web_type: {e}", exc_info=True)
            return f"Error performing web type: {e}"
    else:
        tool_logger.warning("'web_surfer_system' not available or not initialized for web_type.")
        return "Web surfer system is not available for web_type."


if __name__ == "__main__":
    # This block is for direct testing of tools.py.
    # It requires mock objects or a simplified environment.
    logger.info("tools.py executed directly for testing.")

    class MockAybarLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARN: {msg}")
        def error(self, msg, exc_info=False): print(f"ERROR: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")

    class MockWebSurfer:
        def __init__(self):
            self.driver = True
        def navigate_to(self, url: str):
            logging.info(f"MockWebSurfer navigating to {url}")
        def get_current_state_for_llm(self):
            return "Mock page text for LLM.", []
        def perform_web_action(self, action_item: Dict) -> str:
            tool_logger = _get_tool_logger(self) # Using self as mock aybar_instance for logger
            tool_logger.info(f"MockWebSurfer.perform_web_action: {action_item}")
            if action_item.get("action_type") == "click":
                return f"Mock successful click on {action_item.get('target_xpath')}"
            elif action_item.get("action_type") == "type":
                return f"Mock successful type into {action_item.get('target_xpath')} with text '{action_item.get('text')}'"
            return "Mock web action unknown"


    class MockMemorySystem:
        def add_memory(self, layer: str, entry: dict):
            logging.info(f"MockMemorySystem.add_memory to {layer}: {entry}")

    class MockCognitiveSystem:
        def __init__(self):
            self.main_goal = None
            self.sub_goals = []
            self.current_sub_goal_index = -1
            self.goal_duration = 0
            self.goal_start_turn = 0
        def get_current_task(self, current_turn): return self.main_goal
        def clear_all_goals(self):
            self.main_goal = None; self.sub_goals = []; self.current_sub_goal_index = -1
            logging.info("MockCognitiveSystem: Goals cleared.")
        def set_new_goal(self, goal_input, duration, current_turn): # Add this method
            if isinstance(goal_input, str): self.main_goal = goal_input
            elif isinstance(goal_input, dict): self.main_goal = goal_input.get("goal")
            logging.info(f"MockCognitiveSystem: New goal set: {self.main_goal}")

    class MockComputerControlSystem:
        def keyboard_type(self, text:str):
            logging.info(f"MockComputerControlSystem.keyboard_type: {text}")
            return f"Typed: {text}"
        def mouse_click(self, x:int, y:int, double_click:bool=False):
            logging.info(f"MockComputerControlSystem.mouse_click: ({x},{y}), double: {double_click}")
            return f"Clicked at ({x},{y})"
        def analyze_screen_with_vlm(self, question:str):
            logging.info(f"MockComputerControlSystem.analyze_screen_with_vlm: {question}")
            return f"Screen analysis for '{question}': Mock VLM result."


    class MockEnhancedAybar:
        def __init__(self):
            self.logger = MockAybarLogger()
            self.web_surfer_system = MockWebSurfer()
            self.memory_system = MockMemorySystem()
            self.cognitive_system = MockCognitiveSystem()
            self.computer_control_system = MockComputerControlSystem()
            self.current_turn = 0
            self.active_user_id = "test_user_id" # Added for handle_interaction test

        def _perform_internet_search(self, query: str) -> str:
            self.logger.info(f"MockEnhancedAybar._perform_internet_search for query: {query}")
            if hasattr(self, 'memory_system') and self.memory_system:
                 self.memory_system.add_memory("semantic", {
                    "timestamp": "test_time", "turn": self.current_turn,
                    "insight": f"Mock search summary for '{query}'",
                    "source": "internet_search", "query": query
                })
            return f"Mock search summary for '{query}'"

        def _update_identity(self) -> str:
            self.logger.info("MockEnhancedAybar._update_identity called.")
            return "Identity update process initiated (mock)."

        def _creative_generation(self, creation_type: str, theme: str) -> str:
            self.logger.info(f"MockEnhancedAybar._creative_generation called with type: {creation_type}, theme: {theme}")
            return f"Mock creative content: A {creation_type} about {theme}."

        def _regulate_emotion(self, strategy: str) -> str:
            self.logger.info(f"MockEnhancedAybar._regulate_emotion called with strategy: {strategy}")
            return f"Emotion regulation attempted using {strategy} (mock)."

        def _analyze_memory(self, query: str) -> str:
            self.logger.info(f"MockEnhancedAybar._analyze_memory called with query: {query}")
            return f"Memory analysis result for '{query}' (mock)."

        def _run_internal_simulation(self, scenario: str) -> str:
            self.logger.info(f"MockEnhancedAybar._run_internal_simulation called with scenario: {scenario}")
            return f"Internal simulation result for '{scenario}' (mock)."

        def _handle_interaction(self, user_id: str, goal: str, method: str) -> str:
            self.logger.info(f"MockEnhancedAybar._handle_interaction called: User {user_id}, Goal {goal}, Method {method}")
            return f"Interaction response for {user_id} (mock)."

        def _perform_meta_reflection(self, turn_to_analyze: int, thought_to_analyze: str) -> str:
            self.logger.info(f"MockEnhancedAybar._perform_meta_reflection for turn {turn_to_analyze}, thought: {thought_to_analyze}")
            return "Meta-reflection insights (mock)."


    mock_aybar_instance = MockEnhancedAybar()
    # Add aybar_instance.logger to mock web_surfer for its internal logging
    if hasattr(mock_aybar_instance, 'web_surfer_system') and mock_aybar_instance.web_surfer_system:
        mock_aybar_instance.web_surfer_system.logger = mock_aybar_instance.logger


    print("\n--- Testing maps_or_search (URL) ---")
    print(f"Result: {maps_or_search(query='https://www.google.com', aybar_instance=mock_aybar_instance, thought='Test URL navigation')}")

    print("\n--- Testing maps_or_search (Search Term) ---")
    print(f"Result: {maps_or_search(query='python programming best practices', aybar_instance=mock_aybar_instance, thought='Test search query')}")

    print("\n--- Testing ask_user_via_file ---")
    test_question = "Bu bir test sorusudur, nasıl gidiyor?"
    print(f"Result: {ask_user_via_file(question=test_question, aybar_instance=mock_aybar_instance, thought='Test asking user')}")
    if os.path.exists(FROM_AYBAR_FILE):
        with open(FROM_AYBAR_FILE, "r", encoding="utf-8") as f_test:
            print(f"Content of {FROM_AYBAR_FILE}: {f_test.read()}")
        os.remove(FROM_AYBAR_FILE)

    print("\n--- Testing update_identity ---")
    print(f"Result: {update_identity(aybar_instance=mock_aybar_instance, thought='Test identity update')}")

    print("\n--- Testing finish_goal ---")
    mock_aybar_instance.cognitive_system.set_new_goal("Ana hedef", 10, 0)
    print(f"Result: {finish_goal(summary='Başarıyla tamamlandı.', aybar_instance=mock_aybar_instance, thought='Test finishing goal')}")

    print("\n--- Testing summarize_and_reset ---")
    mock_aybar_instance.cognitive_system.set_new_goal("Eski hedef", 10, 0)
    print(f"Result: {summarize_and_reset(aybar_instance=mock_aybar_instance, thought='Kafa karışıklığı nedeniyle reset.')}")
    print(f"Goal after reset: {mock_aybar_instance.cognitive_system.main_goal}")

    print("\n--- Testing creative_generation ---")
    print(f"Result: {creative_generation(creation_type='poem', theme='stars', aybar_instance=mock_aybar_instance, thought='Test poem generation')}")

    print("\n--- Testing regulate_emotion ---")
    print(f"Result: {regulate_emotion(strategy='deep_breathing', aybar_instance=mock_aybar_instance, thought='Test emotion regulation')}")

    print("\n--- Testing analyze_memory ---")
    print(f"Result: {analyze_memory(query='my first memory', aybar_instance=mock_aybar_instance, thought='Test memory analysis')}")

    print("\n--- Testing run_internal_simulation ---")
    print(f"Result: {run_internal_simulation(scenario='what if I could fly?', aybar_instance=mock_aybar_instance, thought='Test simulation')}")

    print("\n--- Testing handle_interaction ---")
    print(f"Result: {handle_interaction(user_id='test_user', goal='build_trust', method='ask_open_question', aybar_instance=mock_aybar_instance, thought='Test interaction')}")

    print("\n--- Testing perform_meta_reflection ---")
    print(f"Result: {perform_meta_reflection(turn_to_analyze=1, thought_to_analyze='initial thought', aybar_instance=mock_aybar_instance, thought='Test meta reflection')}")

    print("\n--- Testing keyboard_type ---")
    print(f"Result: {keyboard_type(text_to_type='Merhaba Dünya!', aybar_instance=mock_aybar_instance, thought='Test typing')}")

    print("\n--- Testing mouse_click ---")
    print(f"Result: {mouse_click(x=100, y=150, aybar_instance=mock_aybar_instance, thought='Test mouse click')}")

    print("\n--- Testing analyze_screen ---")
    print(f"Result: {analyze_screen(question='What is on the screen?', aybar_instance=mock_aybar_instance, thought='Test screen analysis')}")

    print("\n--- Testing web_click ---")
    print(f"Result: {web_click(target_xpath='//button[@id=\"submit\"]', aybar_instance=mock_aybar_instance, thought='Test web click')}")

    print("\n--- Testing web_type ---")
    print(f"Result: {web_type(target_xpath='//input[@name=\"username\"]', text_to_type='aybar_user', aybar_instance=mock_aybar_instance, thought='Test web type')}")


    class MockAybarNoSearch(MockEnhancedAybar):
        def __init__(self):
            super().__init__()
            if hasattr(self, '_perform_internet_search'):
                delattr(self, '_perform_internet_search')

    mock_aybar_no_search_instance = MockAybarNoSearch()
    print("\n--- Testing maps_or_search (Search Term - Missing Method) ---")
    print(f"Result: {maps_or_search(query='another search', aybar_instance=mock_aybar_no_search_instance, thought='Test missing method')}")
