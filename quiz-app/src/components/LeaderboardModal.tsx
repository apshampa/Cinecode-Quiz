import React from 'react';
import { Trophy, Calendar } from 'lucide-react';
import { Storage, LeaderboardEntry } from '../utils/storage';

interface Props {
  onClose: () => void;
}

export const LeaderboardModal: React.FC<Props> = ({ onClose }) => {
  const leaderboard = Storage.getLeaderboard();

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-content" style={{ animation: 'slide-up 0.3s ease', maxWidth: '500px' }}>
        <button className="modal-close" onClick={onClose}>&times;</button>
        
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <Trophy size={48} color="var(--accent)" style={{ marginBottom: '1rem' }} />
          <h2 style={{ fontSize: '2rem', fontWeight: 800 }}>Top Scores</h2>
          <p style={{ color: 'var(--text-muted)' }}>The best CineCode decipherers</p>
        </div>

        {leaderboard.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', background: 'var(--surface-hover)', borderRadius: 'var(--radius)' }}>
            No scores yet. Play a game to get on the board!
          </div>
        ) : (
          <div className="leaderboard-list">
            {leaderboard.map((entry: LeaderboardEntry, idx: number) => (
              <div key={idx} className={`lb-item ${idx === 0 ? 'lb-first' : ''}`}>
                <div className="lb-rank">#{idx + 1}</div>
                <div className="lb-details">
                  <div className="lb-name">{entry.name}</div>
                  <div className="lb-date"><Calendar size={12} style={{ display: 'inline', marginRight: '4px' }} />{new Date(entry.date).toLocaleDateString()}</div>
                </div>
                <div className="lb-score">{entry.score} <span style={{ fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-muted)' }}>pts</span></div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
