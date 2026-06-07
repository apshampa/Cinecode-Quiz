import React from 'react';
import { BarChart3, Lock } from 'lucide-react';
import { Storage, ACHIEVEMENTS } from '../utils/storage';

interface Props {
  onClose: () => void;
}

export const StatsModal: React.FC<Props> = ({ onClose }) => {
  const stats = Storage.getStats();
  
  const accuracy = stats.totalQuestions > 0 
    ? Math.round((stats.totalCorrect / stats.totalQuestions) * 100) 
    : 0;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className="glass-panel modal-content" 
        style={{ animation: 'slide-up 0.3s ease', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="modal-close" onClick={onClose}>&times;</button>
        
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <BarChart3 size={40} color="var(--primary)" style={{ marginBottom: '1rem' }} />
          <h2 style={{ fontSize: '2rem', fontWeight: 800 }}>Stats & Achievements</h2>
        </div>

        {/* STATS SUMMARY */}
        <div className="gameover-stats" style={{ margin: '0 auto 2rem auto', maxWidth: '100%', display: 'flex', justifyContent: 'space-between' }}>
          <div className="summary-stat">
            <span className="stat-val">{stats.gamesPlayed}</span>
            <span className="stat-lbl">Games Played</span>
          </div>
          <div className="summary-stat">
            <span className="stat-val" style={{ color: 'var(--success)' }}>{accuracy}%</span>
            <span className="stat-lbl">Accuracy</span>
          </div>
          <div className="summary-stat">
            <span className="stat-val" style={{ color: '#f59e0b' }}>{stats.highestStreak}</span>
            <span className="stat-lbl">Best Streak</span>
          </div>
        </div>

        {/* ACHIEVEMENTS GRID */}
        <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>Achievements</h3>
        
        <div className="achievements-grid">
          {ACHIEVEMENTS.map(ach => {
            const unlocked = stats.achievements.includes(ach.id);
            return (
              <div key={ach.id} className={`achievement-card ${unlocked ? 'unlocked' : 'locked'}`}>
                <div className="ach-icon">
                  {unlocked ? ach.icon : <Lock size={20} color="var(--text-muted)" />}
                </div>
                <div className="ach-info">
                  <div className="ach-name">{ach.name}</div>
                  <div className="ach-desc">{ach.description}</div>
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
};
