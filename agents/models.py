from pydantic import BaseModel, Field
from typing import List, Optional


class SubSection(BaseModel):
    """Represents a subsection within a blog section"""
    heading: str = Field(..., description="The H3 heading for this subsection")
    description: Optional[str] = Field(None, description="What this subsection should cover")


class BlogSection(BaseModel):
    """Represents a single section in the blog plan"""
    heading: str = Field(..., description="The H2 heading for this section")
    description: Optional[str] = Field(None, description="What this section should cover")
    subsections: List[SubSection] = Field(default_factory=list, description="Optional H3 subsections")


class BlogPlan(BaseModel):
    """Complete blog plan with structure and sections"""
    title: str = Field(..., description="The main title/heading for the blog post")
    intro: Optional[str] = Field(None, description="Optional introduction text or description")
    intro_length_guidance: str = Field(default="moderate", description="Length guidance: 'brief', 'moderate', or 'comprehensive'")
    sections: List[BlogSection] = Field(..., min_length=1, description="List of sections to be written")
    
    def get_section_count(self) -> int:
        """Get the total number of sections in the plan"""
        return len(self.sections)
    
    def get_all_headings(self) -> List[str]:
        """Get list of all section headings"""
        return [section.heading for section in self.sections]


# New models for researcher_v2
class ArticleSubSection(BaseModel):
    """Subsection extracted from an article"""
    heading: str = Field(..., description="The H3 heading")
    description: Optional[str] = Field(None, description="Description/summary")
    text: str = Field(..., description="Raw text content from this subsection")


class ArticleSection(BaseModel):
    """Section extracted from an article"""
    heading: str = Field(..., description="The H2 heading")
    description: Optional[str] = Field(None, description="Description/summary")
    text: str = Field(..., description="Raw text content from this section")
    subsections: List[ArticleSubSection] = Field(default_factory=list, description="Subsections")


class ArticlePlan(BaseModel):
    """Complete article structure with extracted content"""
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Source URL")
    intro: Optional[str] = Field(None, description="Introduction/opening text")
    sections: List[ArticleSection] = Field(..., min_length=1, description="Article sections with content")

