'use client'

import { useState } from 'react'
import { BlogPlan, BlogSection, SubSection } from '@/types/api'
import Header from './Header'
import Footer from './Footer'

interface PlanReviewScreenProps {
  plan: BlogPlan
  onBack: () => void
  onGenerate: (plan: BlogPlan) => void
}

export default function PlanReviewScreen({ plan, onBack, onGenerate }: PlanReviewScreenProps) {
  const [editedPlan, setEditedPlan] = useState<BlogPlan>(plan)
  const [isEditing, setIsEditing] = useState(false)

  const handleTitleChange = (newTitle: string) => {
    setEditedPlan({ ...editedPlan, title: newTitle })
  }

  const handleIntroChange = (newIntro: string) => {
    setEditedPlan({ ...editedPlan, intro: newIntro })
  }

  const handleSectionHeadingChange = (sectionIndex: number, newHeading: string) => {
    const updatedSections = [...editedPlan.sections]
    updatedSections[sectionIndex] = {
      ...updatedSections[sectionIndex],
      heading: newHeading
    }
    setEditedPlan({ ...editedPlan, sections: updatedSections })
  }

  const handleSectionDescriptionChange = (sectionIndex: number, newDescription: string) => {
    const updatedSections = [...editedPlan.sections]
    updatedSections[sectionIndex] = {
      ...updatedSections[sectionIndex],
      description: newDescription
    }
    setEditedPlan({ ...editedPlan, sections: updatedSections })
  }

  const handleSubsectionHeadingChange = (
    sectionIndex: number,
    subsectionIndex: number,
    newHeading: string
  ) => {
    const updatedSections = [...editedPlan.sections]
    const updatedSubsections = [...updatedSections[sectionIndex].subsections]
    updatedSubsections[subsectionIndex] = {
      ...updatedSubsections[subsectionIndex],
      heading: newHeading
    }
    updatedSections[sectionIndex] = {
      ...updatedSections[sectionIndex],
      subsections: updatedSubsections
    }
    setEditedPlan({ ...editedPlan, sections: updatedSections })
  }

  const handleSubsectionDescriptionChange = (
    sectionIndex: number,
    subsectionIndex: number,
    newDescription: string
  ) => {
    const updatedSections = [...editedPlan.sections]
    const updatedSubsections = [...updatedSections[sectionIndex].subsections]
    updatedSubsections[subsectionIndex] = {
      ...updatedSubsections[subsectionIndex],
      description: newDescription
    }
    updatedSections[sectionIndex] = {
      ...updatedSections[sectionIndex],
      subsections: updatedSubsections
    }
    setEditedPlan({ ...editedPlan, sections: updatedSections })
  }

  const handleAddSubsection = (sectionIndex: number) => {
    const updatedSections = [...editedPlan.sections]
    updatedSections[sectionIndex].subsections.push({
      heading: 'New Subsection',
      description: null
    })
    setEditedPlan({ ...editedPlan, sections: updatedSections })
  }

  const handleRemoveSubsection = (sectionIndex: number, subsectionIndex: number) => {
    const updatedSections = [...editedPlan.sections]
    updatedSections[sectionIndex].subsections.splice(subsectionIndex, 1)
    setEditedPlan({ ...editedPlan, sections: updatedSections })
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header showBackButton backUrl="/" backLabel="Back to Home" />

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-4xl mx-auto w-full">
          {/* Page Heading */}
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-text-primary mb-2">
                Blog Outline
              </h1>
              <p className="text-text-secondary text-lg">
                Review and edit the plan below
              </p>
            </div>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="px-4 py-2 bg-accent text-text-primary rounded-lg font-medium hover:bg-opacity-90 transition-all"
            >
              {isEditing ? 'Done Editing' : 'Edit Outline'}
            </button>
          </div>

          {/* Blog Title Card */}
          <div className="mb-6 bg-input-bg/50 rounded-lg p-6 border border-input-bg">
            {isEditing ? (
              <input
                type="text"
                value={editedPlan.title}
                onChange={(e) => handleTitleChange(e.target.value)}
                className="w-full text-3xl font-bold bg-background text-text-primary p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
              />
            ) : (
              <h2 className="text-3xl font-bold text-text-primary">
                {editedPlan.title}
              </h2>
            )}
          </div>

          {/* Introduction Card */}
          {editedPlan.intro && (
            <div className="mb-8 bg-input-bg/50 rounded-lg p-6 border border-input-bg">
              <label className="block text-text-secondary text-sm font-medium mb-3">
                Introduction
              </label>
              {isEditing ? (
                <textarea
                  value={editedPlan.intro}
                  onChange={(e) => handleIntroChange(e.target.value)}
                  placeholder="Enter introduction..."
                  className="w-full min-h-[100px] bg-background text-text-primary p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent resize-y"
                />
              ) : (
                <p className="text-text-secondary text-lg leading-relaxed">
                  {editedPlan.intro}
                </p>
              )}
            </div>
          )}

          {/* Sections */}
          <div className="space-y-6">
            {editedPlan.sections.map((section, sectionIdx) => (
              <div
                key={sectionIdx}
                className="relative bg-input-bg/60 rounded-lg border-l-4 border-accent overflow-hidden shadow-lg"
              >
                {/* Section Content */}
                <div className="p-6">
                  {/* Section Heading */}
                  <div className="mb-3">
                    {isEditing ? (
                      <input
                        type="text"
                        value={section.heading}
                        onChange={(e) => handleSectionHeadingChange(sectionIdx, e.target.value)}
                        className="w-full text-2xl font-bold bg-background text-text-primary p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                      />
                    ) : (
                      <h2 className="text-2xl font-bold text-text-primary">
                        {section.heading}
                      </h2>
                    )}
                  </div>

                  {/* Section Description */}
                  {section.description && (
                    <div className="mb-5">
                      {isEditing ? (
                        <textarea
                          value={section.description}
                          onChange={(e) => handleSectionDescriptionChange(sectionIdx, e.target.value)}
                          placeholder="Section description..."
                          className="w-full min-h-[60px] bg-background text-text-secondary p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent resize-y"
                        />
                      ) : (
                        <p className="text-text-secondary leading-relaxed">
                          {section.description}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Subsections */}
                  {section.subsections.length > 0 && (
                    <div className="relative mt-6 space-y-5">
                      {/* Extend the green line through subsections */}
                      {/* <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-accent/40"></div> */}
                      <div className="pl-6 space-y-5">
                        {section.subsections.map((subsection, subIdx) => (
                          <div
                            key={subIdx}
                            className="relative pl-6 border-l-2 border-accent/60"
                          >
                            {isEditing ? (
                              <div className="space-y-3">
                                <div className="flex items-center gap-3">
                                  <input
                                    type="text"
                                    value={subsection.heading}
                                    onChange={(e) =>
                                      handleSubsectionHeadingChange(sectionIdx, subIdx, e.target.value)
                                    }
                                    className="flex-1 text-xl font-semibold bg-background text-text-primary p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                                  />
                                  <button
                                    onClick={() => handleRemoveSubsection(sectionIdx, subIdx)}
                                    className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 border border-red-400/30 rounded-lg hover:bg-red-400/10 transition-all"
                                  >
                                    Remove
                                  </button>
                                </div>
                                <textarea
                                  value={subsection.description || ''}
                                  onChange={(e) =>
                                    handleSubsectionDescriptionChange(
                                      sectionIdx,
                                      subIdx,
                                      e.target.value
                                    )
                                  }
                                  placeholder="Subsection description..."
                                  className="w-full min-h-[50px] bg-background text-text-secondary p-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent resize-y"
                                />
                              </div>
                            ) : (
                              <div>
                                <h3 className="text-xl font-semibold text-text-primary mb-2">
                                  {subsection.heading}
                                </h3>
                                {subsection.description && (
                                  <p className="text-text-secondary text-sm leading-relaxed">
                                    {subsection.description}
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Add Subsection Button (when editing) */}
                  {isEditing && (
                    <button
                      onClick={() => handleAddSubsection(sectionIdx)}
                      className="mt-6 ml-6 px-4 py-2 text-sm text-accent border border-accent/40 rounded-lg hover:bg-accent/10 transition-all font-medium"
                    >
                      + Add Subsection
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4 mt-12 pt-8 border-t border-input-bg">
            <button
              onClick={onBack}
              className="px-8 py-3 border-2 border-text-secondary text-text-secondary rounded-lg font-semibold hover:border-accent hover:text-accent transition-all"
            >
              Back
            </button>
            <button
              onClick={() => onGenerate(editedPlan)}
              className="flex-1 px-8 py-3 bg-accent text-text-primary rounded-lg font-semibold hover:bg-opacity-90 transition-all shadow-lg hover:shadow-xl"
            >
              Generate Blog Post
            </button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}

