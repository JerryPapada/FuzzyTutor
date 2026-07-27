import React from "react";
import { AlertCircle } from "lucide-react";
import Header from "../components/Header";
import ModulePanel from "../components/ModulePanel";
import TaskPanel from "../components/TaskPanel";
import XAIPanel from "../components/XAIPanel";
import SurveyModal from "../components/SurveyModal";
import ResetModal from "../components/ResetModal";
import HelpModal from "../components/HelpModal";
import useTutorSession from "../hooks/useTutorSession";
import "../pages-css/TutorPage.css";

function TutorPage() {
  const tutor = useTutorSession();

  return (
    <main className="app-shell">
      <Header onHelp={tutor.handleHelp} onReset={tutor.handleReset} />

      {/* Custom Notification Toast */}
      <div className={`custom-notification ${tutor.showNotification ? "show" : ""}`}>
        <div className="custom-notification-icon">
          <AlertCircle size={20} />
        </div>
        <div className="custom-notification-content">
          {tutor.notificationMsg}
        </div>
      </div>

      <section className="workspace">
        <ModulePanel
          modules={tutor.modules}
          session={tutor.session}
          activeModuleId={tutor.activeModuleId}
          onSelectModule={tutor.selectModule}
        />

        <TaskPanel
          activeModule={tutor.activeModule}
          activeModuleId={tutor.activeModuleId}
          activeTask={tutor.activeTask}
          session={tutor.session}
          timeline={tutor.timeline}
          activeTaskIndexInTimeline={tutor.activeTaskIndexInTimeline}
          isReviewMode={tutor.isReviewMode}
          reviewItems={tutor.reviewItems}
          selectedChoice={tutor.selectedChoice}
          onSelectedChoiceChange={tutor.onSelectedChoiceChange}
          codeAnswer={tutor.codeAnswer}
          onCodeAnswerChange={tutor.onCodeAnswerChange}
          isTransitioning={tutor.isTransitioning}
          elapsedSeconds={tutor.elapsedSeconds}
          canGoBack={tutor.canGoBack}
          onGoBack={tutor.goBack}
          canGoForwardReview={tutor.canGoForwardReview}
          onGoForwardReview={tutor.goForwardReview}
          revealingHint={tutor.revealingHint}
          onRequestHint={tutor.requestHint}
          hintState={tutor.hintState}
          onSkip={tutor.skipTask}
          onSubmit={tutor.submitAnswer}
        />

        <XAIPanel
          evaluation={tutor.evaluation}
          showTrace={tutor.showTrace}
          onToggleTrace={tutor.onToggleTrace}
        />
      </section>

      <SurveyModal
        show={tutor.showSurveyModal}
        satisfaction={tutor.satisfaction}
        onSatisfactionChange={tutor.setSatisfaction}
        perceivedDifficulty={tutor.perceivedDifficulty}
        onPerceivedDifficultyChange={tutor.setPerceivedDifficulty}
        confidence={tutor.confidence}
        onConfidenceChange={tutor.setConfidence}
        feedbackComment={tutor.feedbackComment}
        onFeedbackCommentChange={tutor.setFeedbackComment}
        submittingSurvey={tutor.submittingSurvey}
        onSubmit={tutor.handleSurveySubmit}
      />

      <ResetModal
        show={tutor.showResetModal}
        onCancel={() => tutor.setShowResetModal(false)}
        onConfirm={tutor.confirmReset}
      />

      <HelpModal
        show={tutor.showHelpModal}
        onClose={() => tutor.setShowHelpModal(false)}
      />
    </main>
  );
}

export default TutorPage;
