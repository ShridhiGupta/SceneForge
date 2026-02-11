import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles, FileText, Loader2 } from 'lucide-react';
import { api } from '../utils/api';
import toast from 'react-hot-toast';

const CreateVideo = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: '',
    script: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.title.trim() || !formData.script.trim()) {
      toast.error('Please fill in all fields');
      return;
    }

    setIsSubmitting(true);
    
    try {
      const response = await api.post('/videos', formData);
      toast.success('Video creation started successfully!');
      navigate(`/videos/${response.data.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create video');
    } finally {
      setIsSubmitting(false);
    }
  };

  const scriptExamples = [
    {
      title: "Nature Documentary",
      script: "The sun rises over the mountains, painting the sky in shades of orange and pink. Birds begin their morning songs as the forest comes alive with activity. A gentle breeze rustles through the leaves, carrying the scent of pine and earth."
    },
    {
      title: "Space Journey",
      script: "The spacecraft glides silently through the vast emptiness of space. Stars twinkle in the distance like diamonds on black velvet. Earth appears as a blue marble in the viewport, a reminder of home in the infinite cosmos."
    },
    {
      title: "City Life",
      script: "The city streets bustle with energy as people hurry to their destinations. Neon lights begin to glow as dusk settles, painting the urban landscape in vibrant colors. The rhythm of life pulses through every corner of the metropolis."
    }
  ];

  const loadExample = (example) => {
    setFormData({
      title: example.title,
      script: example.script
    });
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center space-x-4 mb-8"
      >
        <button
          onClick={() => navigate('/videos')}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Videos</span>
        </button>
        
        <div className="flex items-center space-x-2">
          <Sparkles className="w-6 h-6 text-yellow-500" />
          <h1 className="text-3xl font-bold text-gray-900">Create New Video</h1>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Form */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-2"
        >
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Title Input */}
            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                Video Title
              </label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="Enter a descriptive title for your video..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                disabled={isSubmitting}
              />
            </div>

            {/* Script Textarea */}
            <div>
              <label htmlFor="script" className="block text-sm font-medium text-gray-700 mb-2">
                Video Script
              </label>
              <textarea
                id="script"
                name="script"
                value={formData.script}
                onChange={handleChange}
                placeholder="Describe your video scene by scene. Each paragraph will become a separate scene in your video..."
                rows={12}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 resize-none"
                disabled={isSubmitting}
              />
              <p className="text-sm text-gray-500 mt-2">
                Each paragraph will be converted into a separate scene with generated images.
              </p>
            </div>

            {/* Submit Button */}
            <motion.button
              type="submit"
              disabled={isSubmitting}
              whileHover={{ scale: isSubmitting ? 1 : 1.02 }}
              whileTap={{ scale: isSubmitting ? 1 : 0.98 }}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 rounded-lg font-medium hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Creating Video...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Create Video</span>
                </>
              )}
            </motion.button>
          </form>
        </motion.div>

        {/* Sidebar */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="space-y-6"
        >
          {/* Examples */}
          <div className="glass-effect rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
              <FileText className="w-5 h-5 text-blue-500" />
              <span>Example Scripts</span>
            </h3>
            
            <div className="space-y-3">
              {scriptExamples.map((example, index) => (
                <motion.button
                  key={index}
                  onClick={() => loadExample(example)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all duration-200"
                >
                  <h4 className="font-medium text-gray-900 mb-1">{example.title}</h4>
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {example.script.substring(0, 80)}...
                  </p>
                </motion.button>
              ))}
            </div>
          </div>

          {/* Tips */}
          <div className="glass-effect rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Tips for Great Videos</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span>Write descriptive scenes with vivid imagery</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span>Each paragraph creates a separate scene</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span>Keep scenes concise for better results</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span>Use emotional and sensory language</span>
              </li>
            </ul>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default CreateVideo;
