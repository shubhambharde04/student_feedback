import { useEffect, useState, useCallback } from "react";
import API from "../api";
import Sidebar from "../components/Sidebar";
import Toast from "../components/Toast";
import { Plus, Edit2, Trash2, List, Network, Save, Copy, Loader2, GripVertical } from "lucide-react";

export default function FormBuilder() {
  const [activeTab, setActiveTab] = useState("questions"); // 'questions' or 'forms'
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  // Question Bank State
  const [questions, setQuestions] = useState([]);
  const [showQuestionModal, setShowQuestionModal] = useState(false);
  const [questionFormData, setQuestionFormData] = useState({
    text: "",
    question_type: "RATING",
    category: "TEACHING",
    weight: 1.0,
    is_required: true,
    order: 0,
    is_active: true
  });
  
  // Forms State
  const [forms, setForms] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [showFormModal, setShowFormModal] = useState(false);
  const [formConfigData, setFormConfigData] = useState({
    name: "",
    description: "",
    session: "",
    is_active: true
  });
  
  // Form<->Question Assignment
  const [managingForm, setManagingForm] = useState(null); // Which form are we currently editing questions for?
  const [formQuestions, setFormQuestions] = useState([]); // question_ids currently assigned to the form
  const [savingForm, setSavingForm] = useState(false);

  const fetchInitialData = useCallback(async () => {
    try {
      const [questionsRes, sessionsRes] = await Promise.all([
        API.get("questions/"),
        API.get("sessions/")
      ]);
      setQuestions(questionsRes.data);
      setSessions(sessionsRes.data);
      if (sessionsRes.data.length > 0) {
        setSelectedSessionId(sessionsRes.data[0].id.toString());
      }
    } catch (err) {
      setToast({ message: "Failed to load data", type: "error" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  useEffect(() => {
    if (activeTab === "forms" && selectedSessionId) {
      fetchFormsForSession();
    }
  }, [activeTab, selectedSessionId]);

  const fetchFormsForSession = async () => {
    try {
      const res = await API.get(`feedback-forms/?session=${selectedSessionId}`);
      setForms(res.data);
    } catch (err) {
      setToast({ message: "Failed to load forms", type: "error" });
    }
  };

  const fetchQuestions = async () => {
    try {
      const res = await API.get("questions/");
      setQuestions(res.data);
    } catch (err) {
      setToast({ message: "Failed to refresh questions", type: "error" });
    }
  };

  // --- QUESTION HANDLERS ---
  const saveQuestion = async (e) => {
    e.preventDefault();
    try {
      if (questionFormData.id) {
        await API.put(`questions/${questionFormData.id}/`, questionFormData);
        setToast({ message: "Question updated", type: "success" });
      } else {
        await API.post("questions/", questionFormData);
        setToast({ message: "Question created", type: "success" });
      }
      setShowQuestionModal(false);
      fetchQuestions();
    } catch (err) {
      setToast({ message: "Error saving question", type: "error" });
    }
  };

  const deleteQuestion = async (id) => {
    if (!window.confirm("Delete this question? It may break existing form mappings if actively used.")) return;
    try {
      await API.delete(`questions/${id}/`);
      setToast({ message: "Question deleted", type: "success" });
      fetchQuestions();
    } catch (err) {
      setToast({ message: "Cannot delete question in use", type: "error" });
    }
  };

  // --- FORM HANDLERS ---
  const saveForm = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formConfigData, session: selectedSessionId };
      if (formConfigData.id) {
        await API.put(`feedback-forms/${formConfigData.id}/`, payload);
        setToast({ message: "Form updated", type: "success" });
      } else {
        await API.post("feedback-forms/", payload);
        setToast({ message: "Form created", type: "success" });
      }
      setShowFormModal(false);
      fetchFormsForSession();
    } catch (err) {
      setToast({ message: "Error saving form", type: "error" });
    }
  };

  const openFormQuestionManager = (form) => {
    setManagingForm(form);
    // Ideally we should fetch form-question mappings if the backend returns them in the form object.
    // If feedback-forms serializer doesn't include question ids directly, we extract an empty list and manage it.
    // Since we created FormQuestionMapping, the form object might have a `questions` list or we might need an endpoint.
    // For now, if the serializer returns `questions`, use them, otherwise default empty.
    const assignedIds = form.questions ? form.questions.map(q => q.id || q) : [];
    setFormQuestions(assignedIds);
  };

  const toggleQuestionInForm = (qId) => {
    setFormQuestions(prev => 
      prev.includes(qId) ? prev.filter(id => id !== qId) : [...prev, qId]
    );
  };

  const saveFormQuestionsMapping = async () => {
    setSavingForm(true);
    try {
      await API.post(`feedback-forms/${managingForm.id}/assign_questions/`, {
        question_ids: formQuestions
      });
      setToast({ message: "Questions mapped to form successfully", type: "success" });
      setManagingForm(null);
      fetchFormsForSession();
    } catch (err) {
      setToast({ message: "Error mapping questions", type: "error" });
    } finally {
      setSavingForm(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mesh flex">
      <Sidebar role="hod" activeSection="formbuilder" />
      <main className="ml-64 flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          <header className="mb-8">
            <h1 className="text-2xl font-bold font-display text-surface-100 flex items-center gap-2">
              <Network className="text-primary-400" /> Dynamics Forms & Question Bank
            </h1>
            <p className="text-surface-400 text-sm mt-1">Manage global questions and construct session-bound feedback forms.</p>
          </header>

          {/* Navigation Tabs */}
          <div className="flex bg-surface-800 p-1 rounded-lg w-fit mb-8 border border-surface-700/50">
            <button
              className={`px-6 py-2 text-sm font-semibold rounded-md transition-all ${
                activeTab === "questions" ? "bg-primary-500 text-white shadow" : "text-surface-400 hover:text-surface-200"
              }`}
              onClick={() => setActiveTab("questions")}
            >
              Question Master
            </button>
            <button
              className={`px-6 py-2 text-sm font-semibold rounded-md transition-all ${
                activeTab === "forms" ? "bg-primary-500 text-white shadow" : "text-surface-400 hover:text-surface-200"
              }`}
              onClick={() => setActiveTab("forms")}
            >
              Feedback Forms
            </button>
          </div>

          {/* QUESTION BANK TAB */}
          {activeTab === "questions" && (
            <div className="animate-fade-in">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold text-surface-200 uppercase tracking-wider">All Available Questions</h3>
                <button
                  onClick={() => {
                    setQuestionFormData({ text: "", question_type: "RATING", category: "TEACHING", weight: 1.0, is_required: true, order: 0, is_active: true });
                    setShowQuestionModal(true);
                  }}
                  className="btn-primary py-2 px-4 text-sm flex items-center gap-2"
                >
                  <Plus size={16} /> Add Question
                </button>
              </div>

              <div className="glass-card overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead className="bg-surface-800/30 border-b border-surface-700/50 text-surface-400">
                    <tr>
                      <th className="p-4 font-medium uppercase tracking-wider">Question</th>
                      <th className="p-4 font-medium uppercase tracking-wider w-32">Type</th>
                      <th className="p-4 font-medium uppercase tracking-wider w-32">Category</th>
                      <th className="p-4 font-medium uppercase tracking-wider w-24">Weight</th>
                      <th className="p-4 font-medium uppercase tracking-wider w-24 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-700/30">
                    {questions.map((q) => (
                      <tr key={q.id} className="hover:bg-surface-800/20 transition-colors">
                        <td className="p-4 text-surface-200">{q.text} {q.is_required && <span className="text-accent-rose">*</span>}</td>
                        <td className="p-4">
                          <span className={`badge ${q.question_type === 'RATING' ? 'badge-excellent' : 'badge-neutral'}`}>
                            {q.question_type}
                          </span>
                        </td>
                        <td className="p-4"><span className="badge badge-neutral">{q.category}</span></td>
                        <td className="p-4 text-surface-300 font-mono">{q.weight}</td>
                        <td className="p-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <button onClick={() => { setQuestionFormData(q); setShowQuestionModal(true); }} className="text-surface-400 hover:text-primary-400"><Edit2 size={16}/></button>
                            <button onClick={() => deleteQuestion(q.id)} className="text-surface-400 hover:text-accent-rose"><Trash2 size={16}/></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* FORMS TAB */}
          {activeTab === "forms" && !managingForm && (
            <div className="animate-fade-in">
              <div className="glass-card p-6 mb-8 border-l-4 border-l-primary-500 flex justify-between items-center">
                <div>
                  <h3 className="text-sm font-bold text-surface-400 uppercase tracking-wider mb-2">Target Academic Session</h3>
                  <select
                    className="input-dark w-64"
                    value={selectedSessionId}
                    onChange={(e) => setSelectedSessionId(e.target.value)}
                  >
                    {sessions.map(s => <option key={s.id} value={s.id}>{s.name} ({s.year})</option>)}
                  </select>
                </div>
                <button
                  onClick={() => {
                    setFormConfigData({ name: "", description: "", is_active: true });
                    setShowFormModal(true);
                  }}
                  className="btn-primary flex items-center gap-2"
                >
                  <Plus size={16} /> New Form Template
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {forms.map(form => (
                  <div key={form.id} className="glass-card p-6 flex flex-col h-full border border-surface-700/50 hover:border-surface-600 transition-colors">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-xl font-bold text-surface-100">{form.name}</h3>
                        <p className="text-sm text-surface-400 mt-1 line-clamp-2">{form.description}</p>
                      </div>
                      <span className={`px-2 py-1 text-xs font-bold rounded ${form.is_active ? 'bg-primary-500/20 text-primary-400' : 'bg-surface-700 text-surface-400'}`}>
                        {form.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </div>
                    
                    <div className="mt-auto pt-6 flex gap-3">
                      <button 
                        onClick={() => openFormQuestionManager(form)}
                        className="flex-1 bg-surface-800 hover:bg-surface-700 text-surface-200 py-2 rounded font-medium flex items-center justify-center gap-2 transition-colors border border-surface-600"
                      >
                        <List size={16} /> Manage Questions
                      </button>
                      <button onClick={() => { setFormConfigData(form); setShowFormModal(true); }} className="w-10 bg-surface-800 flex items-center justify-center hover:text-primary-400 rounded border border-surface-600"><Edit2 size={16} /></button>
                    </div>
                  </div>
                ))}
                {forms.length === 0 && (
                  <div className="col-span-1 border-2 border-dashed border-surface-700 rounded-xl p-12 text-center text-surface-500">
                    <p>No forms constructed for this session.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* FORM QUESTION PLANNER (Sub-view of Forms Tab) */}
          {activeTab === "forms" && managingForm && (
            <div className="animate-fade-in glass-card p-0 overflow-hidden">
              <div className="bg-surface-800 p-6 flex justify-between items-center border-b border-surface-700">
                <div>
                  <h3 className="text-xl font-bold text-surface-100 flex items-center gap-2">
                    <Network size={20} className="text-primary-400"/> Map Questions to: {managingForm.name}
                  </h3>
                  <p className="text-sm text-surface-400 mt-1">Select questions from the bank that should appear on this form.</p>
                </div>
                <div className="flex gap-3">
                  <button onClick={() => setManagingForm(null)} className="px-4 py-2 text-surface-300 hover:text-white transition-colors">Cancel</button>
                  <button 
                    onClick={saveFormQuestionsMapping}
                    disabled={savingForm}
                    className="btn-success flex items-center gap-2"
                  >
                    {savingForm ? <Loader2 className="animate-spin w-4 h-4" /> : <Save size={16} />} Save Mapping
                  </button>
                </div>
              </div>

              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* Bank */}
                  <div>
                    <h4 className="text-sm font-bold text-surface-400 uppercase tracking-wider mb-4 border-b border-surface-700 pb-2">Available Bank</h4>
                    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                      {questions.filter(q => !formQuestions.includes(q.id)).map(q => (
                        <div key={q.id} className="p-3 bg-surface-800/50 rounded border border-surface-700/50 flex items-start gap-3 hover:border-primary-500/30 transition-colors cursor-pointer" onClick={() => toggleQuestionInForm(q.id)}>
                          <div className="mt-1"><Plus size={16} className="text-primary-400" /></div>
                          <div>
                            <p className="text-surface-200 text-sm">{q.text}</p>
                            <div className="flex gap-2 mt-1">
                              <span className="text-[10px] uppercase font-bold text-surface-500 bg-surface-900 px-1.5 rounded">{q.category}</span>
                              <span className="text-[10px] uppercase font-bold text-surface-500 bg-surface-900 px-1.5 rounded">{q.question_type}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {/* Selected */}
                  <div>
                    <h4 className="text-sm font-bold text-accent-emerald uppercase tracking-wider mb-4 border-b border-surface-700 pb-2">Selected for Form ({formQuestions.length})</h4>
                    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                      {formQuestions.length === 0 && <p className="text-surface-500 text-sm p-4 text-center border border-dashed border-surface-700 rounded">Click a question on the left to add it.</p>}
                      {formQuestions.map((qId, index) => {
                        const q = questions.find(x => x.id === qId);
                        if (!q) return null;
                        return (
                          <div key={qId} className="p-3 bg-accent-emerald/5 rounded border border-accent-emerald/20 flex flex-col gap-2">
                             <div className="flex items-start gap-3 justify-between">
                               <div className="flex items-start gap-3">
                                <div className="mt-1 w-6 h-6 rounded bg-surface-800 flex items-center justify-center text-xs font-bold text-surface-400 flex-shrink-0">{index + 1}</div>
                                <div>
                                  <p className="text-surface-100 text-sm">{q.text}</p>
                                  <div className="flex gap-2 mt-1">
                                    <span className="text-[10px] uppercase font-bold text-surface-500 bg-surface-900 px-1.5 rounded">{q.category}</span>
                                  </div>
                                </div>
                               </div>
                               <button onClick={() => toggleQuestionInForm(q.id)} className="text-surface-500 hover:text-accent-rose"><Trash2 size={16}/></button>
                             </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>

      {/* --- MODALS --- */}

      {/* Question Modal */}
      {showQuestionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-900/80 backdrop-blur-sm">
          <div className="glass-card p-6 w-full max-w-lg shadow-2xl shadow-primary-500/10 animate-fade-in border border-surface-600">
            <h3 className="text-xl font-bold mb-4 text-surface-100">{questionFormData.id ? "Edit Question" : "New Question"}</h3>
            <form onSubmit={saveQuestion} className="space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-1">Question Text</label>
                <textarea required value={questionFormData.text} onChange={e => setQuestionFormData({...questionFormData, text: e.target.value})} className="input-field min-h-[80px]" placeholder="e.g. How effective were the teaching methods?" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Type</label>
                  <select value={questionFormData.question_type} onChange={e => setQuestionFormData({...questionFormData, question_type: e.target.value})} className="input-field">
                    <option value="RATING">Rating (1-5)</option>
                    <option value="TEXT">Text Feedback</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-surface-400 mb-1">Category</label>
                  <select value={questionFormData.category} onChange={e => setQuestionFormData({...questionFormData, category: e.target.value})} className="input-field">
                    <option value="TEACHING">Teaching Quality</option>
                    <option value="PUNCTUALITY">Punctuality</option>
                    <option value="CLARITY">Clarity of Explanation</option>
                    <option value="INTERACTION">Interaction</option>
                    <option value="GENERAL">General</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 gap-4 border-t border-surface-700/50 mt-4">
                <label className="flex items-center gap-2 text-surface-300 font-medium">
                  <input type="checkbox" checked={questionFormData.is_required} onChange={e => setQuestionFormData({...questionFormData, is_required: e.target.checked})} className="rounded bg-surface-800 border-surface-600" />
                  Is Required
                </label>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setShowQuestionModal(false)} className="px-4 py-2 hover:bg-surface-700 rounded text-surface-300">Cancel</button>
                  <button type="submit" className="btn-primary">Save Question</button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Form Details Modal */}
      {showFormModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-900/80 backdrop-blur-sm">
          <div className="glass-card p-6 w-full max-w-lg shadow-2xl shadow-primary-500/10 animate-fade-in border border-surface-600">
            <h3 className="text-xl font-bold mb-4 text-surface-100">{formConfigData.id ? "Edit Form Template" : "New Form Template"}</h3>
            <form onSubmit={saveForm} className="space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-1">Form Name</label>
                <input required type="text" value={formConfigData.name} onChange={e => setFormConfigData({...formConfigData, name: e.target.value})} className="input-field" placeholder="e.g. End Semester Feedback 2024" />
              </div>
              <div>
                <label className="block text-sm text-surface-400 mb-1">Description (Optional)</label>
                <textarea value={formConfigData.description} onChange={e => setFormConfigData({...formConfigData, description: e.target.value})} className="input-field min-h-[80px]" placeholder="Instructions to show before the form..." />
              </div>
              <label className="flex items-center gap-2 text-surface-300 font-medium pb-2 border-b border-surface-700/50">
                  <input type="checkbox" checked={formConfigData.is_active} onChange={e => setFormConfigData({...formConfigData, is_active: e.target.checked})} className="rounded bg-surface-800 border-surface-600" />
                  Make this Form Active for the Session
                </label>
              <div className="flex justify-end gap-2 pt-2">
                  <button type="button" onClick={() => setShowFormModal(false)} className="px-4 py-2 hover:bg-surface-700 rounded text-surface-300">Cancel</button>
                  <button type="submit" className="btn-primary">Save Form Configuration</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
