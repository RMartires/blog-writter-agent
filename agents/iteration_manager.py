from typing import List, Dict, Tuple
from langchain.schema import Document
from agents.writer import WriterAgent
from agents.scorer import BlogScorer


class IterationManager:
    """Manages the iterative process of writing, scoring, and rewriting blog posts"""
    
    def __init__(self, config):
        """
        Initialize iteration manager with configuration
        
        Args:
            config: Configuration module with iteration settings
        """
        self.max_iterations = config.MAX_ITERATIONS
        self.min_score_threshold = config.MIN_SCORE_THRESHOLD
        self.verbose = config.VERBOSE_OUTPUT
        self.iteration_history = []
    
    def run_iterations(
        self,
        topic: str,
        target_keywords: List[str],
        context_docs: List[Document],
        writer: WriterAgent,
        scorer: BlogScorer
    ) -> Dict:
        """
        Run the iterative write-score-rewrite process
        
        Args:
            topic: Blog post topic
            target_keywords: List of target keywords for SEO
            context_docs: Retrieved context documents from RAG
            writer: WriterAgent instance
            scorer: BlogScorer instance
            
        Returns:
            Dictionary with best_blog, best_score, iteration_count, and history
        """
        self.iteration_history = []
        best_blog = None
        best_score = 0
        best_iteration = 0
        current_blog = None
        
        for iteration in range(1, self.max_iterations + 1):
            # Step 1: Write or rewrite
            if iteration == 1:
                # Initial generation
                if self.verbose:
                    print(f"\n✍️  Iteration {iteration}/{self.max_iterations}: Generating initial blog post...")
                
                current_blog = writer.generate_blog_post(
                    topic=topic,
                    context_docs=context_docs,
                    style="professional"
                )
                
                word_count = BlogScorer.count_words(current_blog)
                if self.verbose:
                    print(f"✓ Draft complete ({word_count} words)")
            else:
                # Rewrite based on previous score
                if self.verbose:
                    print(f"\n✍️  Iteration {iteration}/{self.max_iterations}: Rewriting based on feedback...")
                
                previous_score = self.iteration_history[-1][1]
                current_blog = writer.rewrite_blog_post(
                    original_blog=current_blog,
                    topic=topic,
                    score_feedback=previous_score,
                    context_docs=context_docs,
                    target_keywords=target_keywords,
                    iteration=iteration
                )
                
                word_count = BlogScorer.count_words(current_blog)
                if self.verbose:
                    print(f"✓ Rewrite complete ({word_count} words)")
            
            # Step 2: Score the blog
            if self.verbose:
                print(f"\n📊 Scoring Iteration {iteration}...")
            
            score_result = scorer.score_blog(
                blog_content=current_blog,
                topic=topic,
                target_keywords=target_keywords
            )
            
            total_score = score_result['total_score']
            passes_threshold = total_score >= self.min_score_threshold
            score_result['passes_threshold'] = passes_threshold
            
            # Store in history
            self.iteration_history.append((iteration, score_result, current_blog))
            
            # Track best version
            if total_score > best_score:
                best_score = total_score
                best_blog = current_blog
                best_iteration = iteration
            
            # Display scoring results
            if self.verbose:
                self._display_scores(score_result, iteration)
            
            # Step 3: Check stopping criteria
            if passes_threshold:
                if self.verbose:
                    print(f"\n✅ Score threshold ({self.min_score_threshold}) reached!")
                    print(f"🎉 Stopping at iteration {iteration}")
                break
            
            # Check if this is the last iteration
            if iteration == self.max_iterations:
                if self.verbose:
                    print(f"\n⏹️  Maximum iterations ({self.max_iterations}) reached")
                break
            
            # Continue to next iteration
            if self.verbose:
                print(f"\n⏩ Below threshold ({self.min_score_threshold}). Continuing to iteration {iteration + 1}...")
        
        # Return results
        return {
            'best_blog': best_blog,
            'best_score': best_score,
            'best_iteration': best_iteration,
            'iteration_count': len(self.iteration_history),
            'history': self.iteration_history,
            'final_score_details': self.iteration_history[-1][1] if self.iteration_history else None
        }
    
    def _display_scores(self, score_result: Dict, iteration: int):
        """Display detailed scoring information"""
        category_scores = score_result['category_scores']
        feedback = score_result['feedback']
        suggestions = score_result['improvement_suggestions']
        total_score = score_result['total_score']
        
        # Display category scores
        for category, score_data in category_scores.items():
            score = score_data['score']
            max_score = score_data['max']
            percentage = (score / max_score * 100) if max_score > 0 else 0
            
            # Format category name
            category_name = category.replace('_', ' ').title()
            category_name = category_name.ljust(20)
            
            # Determine status emoji
            if percentage >= 80:
                status = "✓"
            elif percentage >= 60:
                status = "⚠️"
            else:
                status = "❌"
            
            print(f"   {category_name} {score}/{max_score} ({percentage:.0f}%) {status}")
        
        # Separator
        print("   " + "─" * 50)
        print(f"   {'Total Score'.ljust(20)} {total_score}/100 ({total_score}%)")
        
        # Display improvement suggestions
        if suggestions and total_score < self.min_score_threshold:
            print(f"\n📝 Improvement Suggestions:")
            for i, suggestion in enumerate(suggestions[:5], 1):  # Show top 5
                print(f"   {i}. {suggestion}")
    
    def get_score_progression(self) -> List[Tuple[int, int]]:
        """
        Get score progression across iterations
        
        Returns:
            List of (iteration_number, total_score) tuples
        """
        return [(iteration, score_result['total_score']) 
                for iteration, score_result, _ in self.iteration_history]
    
    def get_best_iteration_details(self) -> Dict:
        """
        Get detailed information about the best scoring iteration
        
        Returns:
            Dictionary with iteration details
        """
        if not self.iteration_history:
            return None
        
        best_iteration = max(self.iteration_history, key=lambda x: x[1]['total_score'])
        
        return {
            'iteration': best_iteration[0],
            'score': best_iteration[1]['total_score'],
            'score_details': best_iteration[1],
            'blog_content': best_iteration[2]
        }

