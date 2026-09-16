import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/auth/AuthProvider';
import {
  Mic,
  MicOff,
  FileText,
  Upload,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Radio,
  Paperclip,
  ChevronRight,
  RefreshCw,
  Play,
  Volume2,
  FileAudio,
  Building2,
  Sparkles,
  PlusCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { claimsApi, ExecutionEvent, ClaimStatus } from '@/api';
import { cn } from '@/lib/utils';

type InputTab = 'text' | 'voice' | 'file';

export default function ClaimIntake() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [activeTab, setActiveTab] = useState<InputTab>('text');

  // Text Tab State
  const [textValue, setTextValue] = useState('');

  // Voice Tab — Web Speech API
  const [isRecording, setIsRecording] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [speechError, setSpeechError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  // Voice Audio File Upload State
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);

  // File Tab State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Pipeline Stepper State
  const [pipelineStep, setPipelineStep] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [createdEvents, setCreatedEvents] = useState<ExecutionEvent[]>([]);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  // Web Speech API Initialization
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        let currentTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript;
        }
        setVoiceTranscript(currentTranscript);
      };

      recognition.onerror = (err: any) => {
        setSpeechError('Microphone / Speech recognition error: ' + err.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    } else {
      setSpeechError(t('intake.speechUnsupported'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      setSpeechError(t('intake.speechUnsupported'));
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      setSpeechError(null);
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (e: any) {
        setSpeechError('Could not start recording: ' + e.message);
      }
    }
  };

  const handleAudioFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioFile(file);
      setAudioUrl(URL.createObjectURL(file));
      setVoiceTranscript(`[Uploaded Audio Log: ${file.name}] Ingested field audio recording.`);
    }
  };

  const removeAudioFile = () => {
    setAudioFile(null);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
  };

  // Submit Claim & Execute Pipeline. A file upload can legitimately yield
  // several claims at once (a multi-row daily report, a multi-sheet
  // spreadsheet, a P6 export, a multi-section scanned diary) -- match/check
  // run for every claim created, not just the first.
  const runPipeline = async (claimText: string, file: File | null = null) => {
    setIsProcessing(true);
    setPipelineError(null);
    setPipelineStep(1); // Intake

    try {
      let events: ExecutionEvent[];
      if (file) {
        const res = await claimsApi.submitFile(file);
        events = res.events;
      } else {
        const res = await claimsApi.submitText(claimText);
        events = [res.event];
      }

      setPipelineStep(2); // Extraction
      await new Promise((r) => setTimeout(r, 600));

      setPipelineStep(3); // Matching
      await Promise.all(
        events.map(async (ev) => {
          const matchRes = await claimsApi.match(ev.event_id);
          ev.status = matchRes.status;
        })
      );

      setPipelineStep(4); // Checks
      await Promise.all(
        events.map(async (ev) => {
          const checkRes = await claimsApi.check(ev.event_id);
          ev.status = checkRes.status;
        })
      );

      setPipelineStep(5); // Supervisor Review
      setCreatedEvents(events);
    } catch (err: any) {
      setPipelineError(err.message || t('intake.pipelineFailed'));
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSubmitText = () => {
    if (!textValue.trim()) return;
    runPipeline(textValue.trim());
  };

  const handleSubmitVoice = () => {
    if (!voiceTranscript.trim() && !audioFile) return;
    runPipeline(voiceTranscript || `Voice upload: ${audioFile?.name}`, audioFile);
  };

  const handleSubmitFile = () => {
    if (!selectedFile) return;
    runPipeline(`Uploaded document: ${selectedFile.name}`, selectedFile);
  };

  const pipelineSteps = [
    { title: t('intake.stepIntakeTitle'), desc: t('intake.stepIntakeDesc') },
    { title: t('intake.stepExtractionTitle'), desc: t('intake.stepExtractionDesc') },
    { title: t('intake.stepMatchingTitle'), desc: t('intake.stepMatchingDesc') },
    { title: t('intake.stepChecksTitle'), desc: t('intake.stepChecksDesc') },
    { title: t('intake.stepReviewTitle'), desc: t('intake.stepReviewDesc') },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
          <PlusCircle className="w-6 h-6 text-indigo-400" />
          {t('intake.title')}
        </h1>
        <p className="text-slate-400 text-xs mt-1">
          {t('intake.subtitle')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Input Form Tabs (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Tab Selector */}
          <div className="flex bg-slate-900 border border-slate-800 p-1.5 rounded-2xl gap-1">
            <button
              type="button"
              onClick={() => setActiveTab('text')}
              className={cn(
                'flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all',
                activeTab === 'text'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              <FileText className="w-4 h-4" /> {t('intake.tabText')}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('voice')}
              className={cn(
                'flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all',
                activeTab === 'voice'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              <Mic className="w-4 h-4" /> {t('intake.tabVoice')}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('file')}
              className={cn(
                'flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all',
                activeTab === 'file'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-400 hover:text-slate-200'
              )}
            >
              <Upload className="w-4 h-4" /> {t('intake.tabFile')}
            </button>
          </div>

          {/* TAB 1: TEXT UPDATE */}
          {activeTab === 'text' && (
            <Card className="bg-slate-900 border-slate-800 text-slate-100">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">{t('intake.textCardTitle')}</CardTitle>
                <CardDescription className="text-slate-400 text-xs">
                  {t('intake.textCardDesc')}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  rows={5}
                  value={textValue}
                  onChange={(e) => setTextValue(e.target.value)}
                  placeholder={t('intake.textPlaceholder')}
                  className="bg-slate-950 border-slate-800 text-slate-100 focus:border-indigo-500 text-sm"
                />

                <Button
                  onClick={handleSubmitText}
                  disabled={isProcessing || !textValue.trim()}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold h-10 shadow-lg shadow-indigo-600/20"
                >
                  {isProcessing ? t('intake.processingClaim') : t('intake.submitText')}
                </Button>
              </CardContent>
            </Card>
          )}

          {/* TAB 2: VOICE INPUT & AUDIO FILE UPLOAD */}
          {activeTab === 'voice' && (
            <Card className="bg-slate-900 border-slate-800 text-slate-100">
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span>{t('intake.voiceCardTitle')}</span>
                  <span className="text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full font-mono">
                    {t('intake.liveRecognition')}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                {speechError && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs rounded-xl">
                    {speechError}
                  </div>
                )}

                {/* Speech Button */}
                <div className="flex flex-col items-center justify-center p-6 bg-slate-950/60 rounded-2xl border border-slate-800 space-y-3">
                  <button
                    type="button"
                    onClick={toggleRecording}
                    className={cn(
                      'w-16 h-16 rounded-full flex items-center justify-center transition-all shadow-xl',
                      isRecording
                        ? 'bg-rose-600 text-white animate-pulse shadow-rose-600/40'
                        : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-indigo-600/30'
                    )}
                  >
                    {isRecording ? <MicOff className="w-8 h-8" /> : <Mic className="w-8 h-8" />}
                  </button>

                  <span className="text-xs text-slate-300 font-semibold">
                    {isRecording ? t('intake.listening') : t('intake.clickToRecord')}
                  </span>
                </div>

                {/* Live Transcript Editable Area */}
                <div className="space-y-1.5">
                  <label className="text-xs text-slate-300 font-semibold">{t('intake.liveTranscript')}</label>
                  <Textarea
                    rows={4}
                    value={voiceTranscript}
                    onChange={(e) => setVoiceTranscript(e.target.value)}
                    placeholder={t('intake.transcriptPlaceholder')}
                    className="bg-slate-950 border-slate-800 text-slate-100 text-xs"
                  />
                </div>

                {/* Upload Audio File Section */}
                <div className="pt-3 border-t border-slate-800 space-y-3">
                  <span className="text-xs font-semibold text-slate-300 block">{t('intake.uploadAudioSection')}</span>
                  <input
                    type="file"
                    ref={audioInputRef}
                    accept="audio/*,.mp3,.wav,.m4a,.ogg,.webm"
                    onChange={handleAudioFileChange}
                    className="hidden"
                  />

                  {!audioFile ? (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => audioInputRef.current?.click()}
                      className="w-full bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800 text-xs h-9"
                    >
                      <FileAudio className="w-4 h-4 mr-2 text-indigo-400" />
                      {t('intake.selectAudioFile')}
                    </Button>
                  ) : (
                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-indigo-300 truncate">{audioFile.name}</span>
                        <Button variant="ghost" size="sm" onClick={removeAudioFile} className="h-6 text-xs text-rose-400">{t('intake.removeAudio')}</Button>
                      </div>
                      {audioUrl && <audio src={audioUrl} controls className="w-full h-8" />}
                    </div>
                  )}
                </div>

                <Button
                  onClick={handleSubmitVoice}
                  disabled={isProcessing || (!voiceTranscript.trim() && !audioFile)}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold h-10 shadow-lg shadow-indigo-600/20"
                >
                  {isProcessing ? t('intake.processingVoice') : t('intake.submitVoice')}
                </Button>
              </CardContent>
            </Card>
          )}

          {/* TAB 3: FILE UPLOAD */}
          {activeTab === 'file' && (
            <Card className="bg-slate-900 border-slate-800 text-slate-100">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">{t('intake.fileCardTitle')}</CardTitle>
                <CardDescription className="text-slate-400 text-xs">
                  {t('intake.fileCardDesc')}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".pdf,.xlsx,.xls,.csv,.txt,.xer,.jpg,.jpeg,.png"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="hidden"
                />

                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-800 hover:border-indigo-500/60 bg-slate-950/60 rounded-2xl p-8 text-center cursor-pointer transition-all space-y-2"
                >
                  <Upload className="w-8 h-8 text-slate-500 mx-auto" />
                  <div className="text-xs text-slate-300 font-semibold">
                    {selectedFile ? selectedFile.name : t('intake.clickToBrowse')}
                  </div>
                  <div className="text-[10px] text-slate-500">{t('intake.supportedFormats')}</div>
                </div>

                <Button
                  onClick={handleSubmitFile}
                  disabled={isProcessing || !selectedFile}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold h-10 shadow-lg shadow-indigo-600/20"
                >
                  {isProcessing ? t('intake.extractingDocument') : t('intake.ingestDocument')}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* RIGHT COLUMN: Pipeline Stepper & Result (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          <Card className="bg-slate-900 border-slate-800 text-slate-100">
            <CardHeader className="pb-3 border-b border-slate-800">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                {t('intake.pipelineTitle')}
              </CardTitle>
            </CardHeader>

            <CardContent className="pt-6 space-y-6">
              {pipelineError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs rounded-xl">
                  {pipelineError}
                </div>
              )}

              {/* Stepper Display */}
              <div className="space-y-4">
                {pipelineSteps.map((st, idx) => {
                  const stepNum = idx + 1;
                  const isCurrent = pipelineStep === stepNum;
                  const isCompleted = pipelineStep > stepNum;

                  return (
                    <div key={idx} className="flex items-center gap-3">
                      <div
                        className={cn(
                          'w-8 h-8 rounded-full flex items-center justify-center font-mono text-xs font-bold shrink-0 transition-all',
                          isCompleted
                            ? 'bg-emerald-600 text-white'
                            : isCurrent
                            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 animate-pulse'
                            : 'bg-slate-950 text-slate-500 border border-slate-800'
                        )}
                      >
                        {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : stepNum}
                      </div>

                      <div className="flex-1">
                        <div className={cn('text-xs font-semibold', isCurrent ? 'text-indigo-600 dark:text-indigo-300' : isCompleted ? 'text-slate-800 dark:text-slate-200' : 'text-slate-500')}>
                          {st.title}
                        </div>
                        <div className="text-[10px] text-slate-500">{st.desc}</div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Created Events Result Card(s) -- a file upload can yield
                  several claims at once (a multi-row report, a multi-sheet
                  spreadsheet, a P6 export), so this lists every claim
                  created, not just one. */}
              {createdEvents.length > 0 && (
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-900 dark:text-emerald-200 space-y-3 animate-in fade-in duration-300">
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-800 dark:text-emerald-300">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    {t('intake.ingestionComplete')} — {createdEvents.length === 1 ? t('intake.oneClaim') : t('intake.nClaims', { count: createdEvents.length })} {t('intake.queuedForSupervisor')}
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {createdEvents.map((ev) => (
                      <p key={ev.event_id} className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                        {ev.reported_activity_id && (
                          <span className="font-mono text-indigo-600 dark:text-indigo-300 mr-1">{ev.reported_activity_id}</span>
                        )}
                        {t('intake.claimIdLabel')} <span className="font-mono font-bold text-slate-900 dark:text-white">{ev.event_id}</span> {t('intake.statusSetTo')} <span className="font-mono text-amber-600 dark:text-amber-400 font-bold">{ev.status}</span>.
                      </p>
                    ))}
                  </div>
                  <Button
                    onClick={() => navigate(`/review?event_id=${createdEvents[0].event_id}`)}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold h-8"
                  >
                    {t('intake.openReviewWorkspace')}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
