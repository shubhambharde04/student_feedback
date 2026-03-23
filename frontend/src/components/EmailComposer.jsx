import React, { useState } from 'react';
import API from '../api';

export default function EmailComposer({ 
  teachers, 
  subjects, 
  onEmailSent, 
  onClose 
}) {
  const [selectedTeachers, setSelectedTeachers] = useState([]);
  const [customEmails, setCustomEmails] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [emailMessage, setEmailMessage] = useState('');
  const [attachReport, setAttachReport] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const handleSendEmail = async () => {
    const allEmails = [
      ...selectedTeachers.map(id => teachers.find(t => t.id.toString() === id.toString())?.email).filter(Boolean),
      ...customEmails.split(',').map(e => e.trim()).filter(e => e.includes('@'))
    ];

    if (allEmails.length === 0 || !emailSubject || !emailMessage) {
      setError('Please provide at least one valid recipient, subject, and message');
      return;
    }

    setSending(true);
    setError('');

    try {
      const response = await API.post('hod/send-report-emails/', {
        emails: allEmails,
        subject: emailSubject,
        message: emailMessage,
        attach_report: attachReport // currently skipped attached logic
      });

      onEmailSent && onEmailSent(response.data);
      onClose && onClose();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to send email');
    } finally {
      setSending(false);
    }
  };

  const handleTeacherSelect = (e) => {
    const options = e.target.options;
    const selected = [];
    for (let i = 0; i < options.length; i++) {
      if (options[i].selected) selected.push(options[i].value);
    }
    setSelectedTeachers(selected);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="glass-card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-surface-100 font-display">Send Email to Teacher</h3>
          <button
            onClick={onClose}
            className="text-surface-400 hover:text-surface-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-accent-rose/10 border border-accent-rose/20 text-accent-rose">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              Select Teachers (Hold Ctrl/Cmd to select multiple)
            </label>
            <select
              multiple
              value={selectedTeachers}
              onChange={handleTeacherSelect}
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-surface-100 focus:outline-none focus:ring-2 focus:ring-primary-500 min-h-[100px]"
            >
              {teachers.map(teacher => (
                <option key={teacher.id} value={teacher.id}>
                  {teacher.name} ({teacher.email})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              Custom Emails (comma-separated)
            </label>
            <input
              type="text"
              value={customEmails}
              onChange={(e) => setCustomEmails(e.target.value)}
              placeholder="e.g. principal@school.edu, external@user.com"
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              Email Subject *
            </label>
            <input
              type="text"
              value={emailSubject}
              onChange={(e) => setEmailSubject(e.target.value)}
              placeholder="Enter email subject..."
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              Message *
            </label>
            <textarea
              value={emailMessage}
              onChange={(e) => setEmailMessage(e.target.value)}
              placeholder="Type your message here..."
              rows={6}
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <input 
              type="checkbox" 
              id="attachReport"
              checked={attachReport}
              onChange={(e) => setAttachReport(e.target.checked)}
              className="w-4 h-4 text-primary-500 rounded border-surface-700 focus:ring-primary-500 bg-surface-800"
            />
            <label htmlFor="attachReport" className="text-sm font-medium text-surface-300">
              Attach Data (JSON format)
            </label>
          </div>
          
          <div className="flex gap-3 pt-4">
            <button
              onClick={handleSendEmail}
              disabled={sending || (selectedTeachers.length === 0 && !customEmails) || !emailSubject || !emailMessage}
              className="btn-success flex-1 flex items-center justify-center gap-2"
            >
              {sending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  Send Email
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
