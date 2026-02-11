import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Download, Image, Film, Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { api } from '../utils/api';
import toast from 'react-hot-toast';

const VideoDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchVideoDetail();
    
    // Set up polling for updates
    const interval = setInterval(() => {
      if (video && video.status !== 'completed' && video.status !== 'failed') {
        fetchVideoDetail();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [id]);

  const fetchVideoDetail = async () => {
    try {
      const response = await api.get(`/videos/${id}`);
      setVideo(response.data);
    } catch (error) {
      toast.error('Failed to fetch video details');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchVideoDetail();
    setRefreshing(false);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'processing':
      case 'generating_images':
      case 'generating_clips':
      case 'rendering':
        return <Clock className="w-5 h-5 text-blue-600 animate-spin" />;
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'status-pending',
      processing: 'status-processing',
      generating_images: 'status-generating_images',
      generating_clips: 'status-generating_clips',
      rendering: 'status-rendering',
      completed: 'status-completed',
      failed: 'status-failed',
    };
    return colors[status] || 'status-pending';
  };

  const getSceneStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-blue-600 animate-spin" />;
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-600" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full"
        />
      </div>
    );
  }

  if (!video) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Video not found</h2>
          <button
            onClick={() => navigate('/videos')}
            className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors"
          >
            Back to Videos
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-8"
      >
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/videos')}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back to Videos</span>
          </button>
          
          <div className="flex items-center space-x-3">
            <h1 className="text-3xl font-bold text-gray-900">{video.title}</h1>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="p-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className={`flex items-center space-x-2 ${getStatusColor(video.status)}`}>
            {getStatusIcon(video.status)}
            <span className="font-medium capitalize">
              {video.status.replace('_', ' ')}
            </span>
          </div>
          
          {video.final_video_path && (
            <button
              onClick={() => window.open(video.final_video_path, '_blank')}
              className="flex items-center space-x-2 bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </button>
          )}
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Video Preview */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-effect rounded-xl p-6"
          >
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center space-x-2">
              <Film className="w-5 h-5 text-blue-500" />
              <span>Video Preview</span>
            </h2>
            
            <div className="aspect-video bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center">
              {video.final_video_path ? (
                <video
                  controls
                  className="w-full h-full rounded-lg"
                  src={video.final_video_path}
                />
              ) : (
                <div className="text-center">
                  <Play className="w-16 h-16 text-blue-500 mx-auto mb-4" />
                  <p className="text-gray-600">Video will appear here when ready</p>
                </div>
              )}
            </div>
          </motion.div>

          {/* Progress */}
          {video.progress > 0 && video.status !== 'completed' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-effect rounded-xl p-6"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Generation Progress</h3>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <motion.div
                  className="progress-bar h-3 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${video.progress}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <p className="text-sm text-gray-600 mt-2">{Math.round(video.progress)}% Complete</p>
            </motion.div>
          )}

          {/* Script */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-effect rounded-xl p-6"
          >
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Original Script</h2>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-700 whitespace-pre-wrap">{video.script}</p>
            </div>
          </motion.div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Scenes */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-effect rounded-xl p-6"
          >
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
              <Image className="w-5 h-5 text-purple-500" />
              <span>Scenes ({video.scenes?.length || 0})</span>
            </h3>
            
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {video.scenes?.map((scene, index) => (
                <motion.div
                  key={scene.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="bg-white rounded-lg p-3 border border-gray-200"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-900">Scene {scene.scene_number}</h4>
                    {getSceneStatusIcon(scene.image_generation_status)}
                  </div>
                  
                  <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                    {scene.description}
                  </p>
                  
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{scene.duration}s</span>
                    {scene.image_path && (
                      <button
                        onClick={() => window.open(scene.image_path, '_blank')}
                        className="text-blue-500 hover:text-blue-700"
                      >
                        View Image
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Error Message */}
          {video.error_message && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-red-50 border border-red-200 rounded-xl p-4"
            >
              <h4 className="font-medium text-red-900 mb-2">Error Details</h4>
              <p className="text-sm text-red-700">{video.error_message}</p>
            </motion.div>
          )}

          {/* Metadata */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-effect rounded-xl p-6"
          >
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Video Information</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Created:</span>
                <span className="text-gray-900">
                  {new Date(video.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className="text-gray-900 capitalize">
                  {video.status.replace('_', ' ')}
                </span>
              </div>
              {video.completed_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Completed:</span>
                  <span className="text-gray-900">
                    {new Date(video.completed_at).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default VideoDetail;
