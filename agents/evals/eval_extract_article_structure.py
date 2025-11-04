import json
import time
import asyncio
import os
import sys
from dotenv import load_dotenv
from deepeval.dataset import EvaluationDataset
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric
from deepeval import evaluate
from browser_use.llm import ChatOpenRouter
import traceback

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Import the modules
from agents.researcher_v2 import ResearchAgentV2
import config

# Load environment variables
load_dotenv()

# Configuration for rate limiting
ENABLE_THROTTLING = True  # Set to False to use parallel evaluation
THROTTLE_DELAY_SECONDS = 5  # Delay between evaluations in seconds

def create_test_dataset():
    """Create a test dataset for article extraction evaluation"""
    test_cases = [
        {
            "url": "https://clearbit.com/blog/tam-icp-and-personas",
            "title": "TAM, ICP, and Personas: What's the difference?",
            "expected_output": "Should extract article structure with title, intro, sections, and HTML content",
            "description": "Test Clearbit blog article extraction for TAM, ICP, and Personas content"
        }
    ]
    return test_cases

async def extract_article_structure_wrapper(url: str, title: str = None) -> str:
    """
    Wrapper function to call the _extract_article_structure method
    Returns a string representation of the extracted article
    """
    try:
        # Initialize the research agent
        if not config.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        agent = ResearchAgentV2(api_key=config.OPENROUTER_API_KEY)
        
        # Call the private method
        article_plan = await agent._extract_article_structure(url, title or "Test Article")
        
        if article_plan:
            # Convert to string representation for evaluation
            result = {
                "title": article_plan.title,
                "url": article_plan.url,
                "intro": article_plan.intro,
                "sections_count": len(article_plan.sections),
                "sections": [
                    {
                        "title": section.title,
                        "subsections_count": len(section.subsections),
                        "content_preview": section.content[:200] + "..." if len(section.content) > 200 else section.content
                    }
                    for section in article_plan.sections
                ]
            }
            return json.dumps(result, indent=2)
        else:
            return "No article content extracted"
            
    except Exception as e:
        return f"Error extracting article: {str(e)}"

async def main():
    print("🚀 Starting LLM Evaluation for Article Structure Extraction")
    
    # Step 1: Create a dataset
    print("\n1. Creating test dataset...")
    test_data = create_test_dataset()
    
    # Step 2: Configure LLM for evaluation
    print("2. Setting up evaluation LLM with OpenRouter...")
    
    # Check if OpenRouter API key is available
    if not os.getenv('OPENROUTER_API_KEY'):
        print("⚠️  Warning: OPENROUTER_API_KEY not found in environment variables")
        return
    
    # Configure deepeval to use OpenRouter for evaluation
    try:

        eval_llm = ChatOpenRouter(
            model=config.OPENROUTER_MODEL,
            api_key=config.OPENROUTER_API_KEY,
            temperature=0.7,
        )
        
        # Create metrics with the configured LLM
        relevancy = AnswerRelevancyMetric(model=eval_llm)
        
        print("✅ Successfully configured LocalModel for evaluation")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not configure LocalModel: {e}")
        
        # Fallback to environment variables approach
        try:
            print("   Trying environment variables approach...")
            # Set environment variables for OpenRouter
            os.environ["OPENAI_API_KEY"] = os.getenv('OPENROUTER_API_KEY')
            os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
            
            # Use default metrics which should now use OpenRouter
            relevancy = AnswerRelevancyMetric()
            print("✅ Successfully configured OpenRouter using environment variables")
            
        except Exception as e2:
            print(f"⚠️  Warning: Could not configure OpenRouter: {e2}")
            print("   Falling back to default configuration (may require OpenAI API key)")
            relevancy = AnswerRelevancyMetric()
    
    # Step 3: Create test cases and run evaluation
    print("3. Creating test cases and running evaluation...")
    
    # Create dataset object
    dataset = EvaluationDataset()
    
    # Convert test data into test cases
    for test_item in test_data:
        print(f"   Processing: {test_item['url']}")
        
        # Get actual output from your article extraction function
        actual_output = await extract_article_structure_wrapper(
            test_item['url'], 
            test_item.get('title')
        )
        
        # Ensure actual_output is always a string
        actual_output = str(actual_output) if actual_output is not None else "No output generated"

        print(actual_output)
        
        # Create test case
        test_case = LLMTestCase(
            input=f"Extract article structure from URL: {test_item['url']}",
            actual_output=actual_output,
            expected_output=test_item['expected_output']
        )
        
        # Add to dataset
        dataset.add_test_case(test_case)
    
    # Step 4: Run evaluation with throttling
    print("4. Running evaluation...")
    try:
        if ENABLE_THROTTLING:
            print("   Using throttled evaluation to avoid rate limits...")
            # Sequential evaluation with delays
            results = []
            for i, test_case in enumerate(dataset.test_cases):
                print(f"   Evaluating test case {i+1}/{len(dataset.test_cases)}...")
                try:
                    result = evaluate(
                        test_cases=[test_case], 
                        metrics=[relevancy]
                    )
                    results.append(result)
                    print(f"   ✅ Test case {i+1} completed")
                except Exception as e:
                    print(f"   ❌ Test case {i+1} failed: {e}")
                    results.append(None)
                
                # Add delay between evaluations
                if i < len(dataset.test_cases) - 1:  # Don't delay after the last one
                    print(f"   ⏳ Waiting {THROTTLE_DELAY_SECONDS} seconds before next evaluation...")
                    time.sleep(THROTTLE_DELAY_SECONDS)
            
            # Filter out failed evaluations
            results = [r for r in results if r is not None]
            
        print("\n✅ Evaluation completed!")
        print(f"Results: {results}")
        
        # Print detailed results
        print("\n📊 Detailed Results:")
        for i, test_case in enumerate(dataset.test_cases):
            print(f"\nTest Case {i+1}:")
            print(f"  Input: {test_case.input}")
            print(f"  Expected: {test_case.expected_output}")
            print(f"  Actual: {test_case.actual_output[:500]}...")  # Truncate for readability
            if hasattr(test_case, 'score') and test_case.score is not None:
                print(f"  Score: {test_case.score}")
                
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Run the evaluation
    asyncio.run(main())
