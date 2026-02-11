import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Plus, Play, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { api } from '../utils/api';
import toast from 'react-hot-toast';

const VideoList = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const response = await api.get('/videos');
      setVideos(response.data);
    } catch (error) {
      toast.error('Failed to fetch videos');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'processing':
      case 'generating_images':
      case 'generating_clips':
      case 'rendering':
        return <Clock className="w-4 h-4 text-blue-600 animate-spin" />;
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-600" />;
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center mb-8"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Your Videos</h1>
          <p className="text-gray-600 mt-1">Manage and track your AI-generated videos</p>
        </div>
        
        <Link
          to="/videos/create"
          className="flex items-center space-x-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-3 rounded-lg hover:shadow-lg transition-all duration-200 hover:scale-105"
        >
          <Plus className="w-5 h-5" />
          <span>Create Video</span>
        </Link>
      </motion.div>

      {/* Video Grid */}
      {videos.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16"
        >
          <div className="w-24 h-24 bg-gray-200 rounded-full mx-auto mb-4 flex items-center justify-center">
            <Play className="w-12 h-12 text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No videos yet</h3>
          <p className="text-gray-500 mb-6">Create your first AI-generated video to get started</p>
          <Link
            to="/videos/create"
            className="inline-flex items-center space-x-2 bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 transition-colors"
          >
            <Plus className="w-5 h-5" />
            <span>Create Your First Video</span>
          </Link>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <AnimatePresence>
            {videos.map((video) => (
              <motion.div
                key={video.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                whileHover={{ y: -5 }}
                className="glass-effect rounded-xl p-6 hover:shadow-xl transition-all duration-300"
              >
                {/* Video Thumbnail Placeholder */}
                <div className="w-full h-40 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg mb-4 flex items-center justify-center">
                  <Play className="w-12 h-12 text-blue-500" />
                </div>

                {/* Video Info */}
                <h3 className="text-lg font-semibold text-gray-900 mb-2 truncate">
                  {video.title}
                </h3>
                
                <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                  {video.script.substring(0, 100)}...
                </p>

                {/* Status Badge */}
                <div className="flex items-center justify-between mb-4">
                  <div className={`flex items-center space-x-2 ${getStatusColor(video.status)}`}>
                    {getStatusIcon(video.status)}
                    <span className="text-xs font-medium capitalize">
                      {video.status.replace('_', ' ')}
                    </span>
                  </div>
                  
                  {video.progress > 0 && video.status !== 'completed' && (
                    <span className="text-sm text-gray-600">
                      {Math.round(video.progress)}%
                    </span>
                  )}
                </div>

                {/* Progress Bar */}
                {video.progress > 0 && video.status !== 'completed' && (
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                    <motion.div
                      className="progress-bar h-2 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${video.progress}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                )}

                {/* Actions */}
                <div className="flex space-x-2">
                  <Link
                    to={`/videos/${video.id}`}
                    className="flex-1 text-center bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 transition-colors text-sm font-medium"
                  >
                    View Details
                  </Link>
                  
                  {video.final_video_path && (
                    <button
                      onClick={() => window.open(video.final_video_path, '_blank')}
                      className="flex-1 text-center bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 transition-colors text-sm font-medium"
                    >
                      Download
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};

export default VideoList;
