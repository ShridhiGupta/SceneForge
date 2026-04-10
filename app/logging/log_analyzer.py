import json
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import numpy as np
from collections import defaultdict, Counter


class LogAnalyzer:
    """Production log analyzer for metrics and improvement tracking"""
    
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {}
    
    def load_logs_from_file(self, file_path: str):
        """Load logs from JSON log file"""
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        self.logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            print(f"Log file not found: {file_path}")
        except Exception as e:
            print(f"Error loading logs: {e}")
    
    def load_logs_from_string(self, log_data: str):
        """Load logs from string data"""
        for line in log_data.split('\n'):
            if line.strip():
                try:
                    log_entry = json.loads(line.strip())
                    self.logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analyze failure patterns and types"""
        failures = [log for log in self.logs if log.get('event_type') == 'task_failure']
        
        failure_types = Counter()
        failure_reasons = Counter()
        failure_by_task = Counter()
        failure_by_agent = Counter()
        
        for failure in failures:
            failure_type = failure.get('failure_type', 'unknown')
            task_name = failure.get('task_name', 'unknown')
            agent_name = failure.get('agent_name', 'unknown')
            error = failure.get('error', 'unknown')
            
            failure_types[failure_type] += 1
            failure_by_task[task_name] += 1
            failure_by_agent[agent_name] += 1
            failure_reasons[error] += 1
        
        return {
            "total_failures": len(failures),
            "failure_types": dict(failure_types),
            "failure_by_task": dict(failure_by_task),
            "failure_by_agent": dict(failure_by_agent),
            "top_failure_reasons": dict(failure_reasons.most_common(10))
        }
    
    def analyze_action_effectiveness(self) -> Dict[str, Any]:
        """Analyze effectiveness of different actions taken"""
        decisions = [log for log in self.logs if log.get('event_type') == 'decision']
        
        action_outcomes = defaultdict(lambda: {'success_count': 0, 'total_count': 0, 'avg_confidence': 0, 'confidence_sum': 0})
        
        for decision in decisions:
            action = decision.get('action', 'unknown')
            confidence = decision.get('confidence', 0)
            
            action_outcomes[action]['total_count'] += 1
            action_outcomes[action]['confidence_sum'] += confidence
        
        # Calculate success rates (would need to link decisions to task outcomes)
        for action in action_outcomes:
            total = action_outcomes[action]['total_count']
            if total > 0:
                action_outcomes[action]['avg_confidence'] = action_outcomes[action]['confidence_sum'] / total
        
        return {
            "total_decisions": len(decisions),
            "action_effectiveness": dict(action_outcomes),
            "most_common_actions": Counter(d.get('action', 'unknown') for d in decisions).most_common(5)
        }
    
    def analyze_retry_patterns(self) -> Dict[str, Any]:
        """Analyze retry patterns and effectiveness"""
        retries = [log for log in self.logs if log.get('event_type') == 'retry']
        
        retry_stats = {
            "total_retries": len(retries),
            "retry_by_task": Counter(),
            "retry_distribution": Counter(),
            "retry_success_rate": 0
        }
        
        for retry in retries:
            task_name = retry.get('task_name', 'unknown')
            retry_count = retry.get('retry_count', 0)
            
            retry_stats['retry_by_task'][task_name] += 1
            retry_stats['retry_distribution'][retry_count] += 1
        
        # Calculate retry success rate (simplified)
        retry_tasks = set(retry.get('task_id') for retry in retries)
        successful_retries = 0
        
        for task_id in retry_tasks:
            task_logs = [log for log in self.logs if log.get('task_id') == task_id]
            has_success = any(log.get('event_type') == 'task_success' for log in task_logs)
            if has_success:
                successful_retries += 1
        
        if retry_tasks:
            retry_stats['retry_success_rate'] = successful_retries / len(retry_tasks)
        
        return retry_stats
    
    def analyze_cost_metrics(self) -> Dict[str, Any]:
        """Analyze cost metrics and optimization"""
        cost_logs = [log for log in self.logs if log.get('event_type') == 'cost_metrics']
        
        cost_stats = {
            "total_cost": 0,
            "cost_by_task": defaultdict(float),
            "cost_by_agent": defaultdict(float),
            "cost_trends": [],
            "cost_optimizations": 0
        }
        
        for cost_log in cost_logs:
            cost = cost_log.get('cost', 0)
            task_name = cost_log.get('task_name', 'unknown')
            agent_name = cost_log.get('agent_name', 'unknown')
            
            cost_stats['total_cost'] += cost
            cost_stats['cost_by_task'][task_name] += cost
            cost_stats['cost_by_agent'][agent_name] += cost
        
        # Analyze cost trends over time
        cost_logs_sorted = sorted(cost_logs, key=lambda x: x.get('timestamp', ''))
        for i, cost_log in enumerate(cost_logs_sorted):
            if i > 0:
                prev_cost = cost_logs_sorted[i-1].get('cost', 0)
                curr_cost = cost_log.get('cost', 0)
                cost_stats['cost_trends'].append(curr_cost - prev_cost)
        
        return {
            "total_cost": cost_stats['total_cost'],
            "cost_by_task": dict(cost_stats['cost_by_task']),
            "cost_by_agent": dict(cost_stats['cost_by_agent']),
            "average_cost_per_task": cost_stats['total_cost'] / len(cost_logs) if cost_logs else 0,
            "cost_variance": np.var(cost_stats['cost_trends']) if cost_stats['cost_trends'] else 0
        }
    
    def analyze_quality_metrics(self) -> Dict[str, Any]:
        """Analyze quality metrics and improvements"""
        quality_logs = [log for log in self.logs if log.get('event_type') == 'quality_metrics']
        
        quality_stats = {
            "total_evaluations": len(quality_logs),
            "quality_before_scores": [],
            "quality_after_scores": [],
            "improvements": [],
            "quality_by_task": defaultdict(list),
            "quality_trends": []
        }
        
        for quality_log in quality_logs:
            quality_before = quality_log.get('quality_before')
            quality_after = quality_log.get('quality_after')
            task_name = quality_log.get('task_name', 'unknown')
            
            if quality_before is not None:
                quality_stats['quality_before_scores'].append(quality_before)
            if quality_after is not None:
                quality_stats['quality_after_scores'].append(quality_after)
                quality_stats['quality_by_task'][task_name].append(quality_after)
            
            if quality_before is not None and quality_after is not None:
                improvement = quality_after - quality_before
                quality_stats['improvements'].append(improvement)
        
        # Calculate statistics
        before_scores = quality_stats['quality_before_scores']
        after_scores = quality_stats['quality_after_scores']
        improvements = quality_stats['improvements']
        
        return {
            "total_evaluations": quality_stats['total_evaluations'],
            "average_quality_before": np.mean(before_scores) if before_scores else 0,
            "average_quality_after": np.mean(after_scores) if after_scores else 0,
            "average_improvement": np.mean(improvements) if improvements else 0,
            "improvement_rate": len([i for i in improvements if i > 0]) / len(improvements) if improvements else 0,
            "quality_variance": np.var(after_scores) if after_scores else 0,
            "best_improvement": max(improvements) if improvements else 0,
            "worst_improvement": min(improvements) if improvements else 0
        }
    
    def analyze_execution_time(self) -> Dict[str, Any]:
        """Analyze execution time metrics"""
        task_logs = [log for log in self.logs if log.get('event_type') in ['task_success', 'task_failure']]
        
        execution_times = []
        times_by_task = defaultdict(list)
        times_by_agent = defaultdict(list)
        
        for log in task_logs:
            exec_time = log.get('execution_time_ms', 0)
            task_name = log.get('task_name', 'unknown')
            agent_name = log.get('agent_name', 'unknown')
            
            if exec_time > 0:
                execution_times.append(exec_time)
                times_by_task[task_name].append(exec_time)
                times_by_agent[agent_name].append(exec_time)
        
        return {
            "total_tasks": len(task_logs),
            "average_execution_time": np.mean(execution_times) if execution_times else 0,
            "median_execution_time": np.median(execution_times) if execution_times else 0,
            "execution_time_variance": np.var(execution_times) if execution_times else 0,
            "slowest_task": max(execution_times) if execution_times else 0,
            "fastest_task": min(execution_times) if execution_times else 0,
            "times_by_task": {task: np.mean(times) for task, times in times_by_task.items()},
            "times_by_agent": {agent: np.mean(times) for agent, times in times_by_agent.items()}
        }
    
    def calculate_improvement_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive improvement metrics"""
        failure_analysis = self.analyze_failure_patterns()
        action_analysis = self.analyze_action_effectiveness()
        retry_analysis = self.analyze_retry_patterns()
        cost_analysis = self.analyze_cost_metrics()
        quality_analysis = self.analyze_quality_metrics()
        time_analysis = self.analyze_execution_time()
        
        # Calculate improvement indicators
        improvement_metrics = {
            "quality_improvement_score": 0,
            "failure_reduction_score": 0,
            "cost_efficiency_score": 0,
            "time_efficiency_score": 0,
            "overall_improvement_score": 0
        }
        
        # Quality improvement score (0-100)
        avg_improvement = quality_analysis.get('average_improvement', 0)
        improvement_rate = quality_analysis.get('improvement_rate', 0)
        improvement_metrics['quality_improvement_score'] = min(100, (avg_improvement * 100) + (improvement_rate * 50))
        
        # Failure reduction score (0-100)
        total_failures = failure_analysis.get('total_failures', 0)
        retry_success_rate = retry_analysis.get('retry_success_rate', 0)
        if total_failures > 0:
            improvement_metrics['failure_reduction_score'] = max(0, 100 - (total_failures * 10) + (retry_success_rate * 30))
        else:
            improvement_metrics['failure_reduction_score'] = 100
        
        # Cost efficiency score (0-100)
        avg_cost = cost_analysis.get('average_cost_per_task', 0)
        if avg_cost > 0:
            improvement_metrics['cost_efficiency_score'] = max(0, 100 - (avg_cost * 100))
        else:
            improvement_metrics['cost_efficiency_score'] = 100
        
        # Time efficiency score (0-100)
        avg_time = time_analysis.get('average_execution_time', 0)
        if avg_time > 0:
            improvement_metrics['time_efficiency_score'] = max(0, 100 - (avg_time / 100))  # Normalize by 100ms
        else:
            improvement_metrics['time_efficiency_score'] = 100
        
        # Overall improvement score (weighted average)
        weights = {
            'quality_improvement_score': 0.3,
            'failure_reduction_score': 0.3,
            'cost_efficiency_score': 0.2,
            'time_efficiency_score': 0.2
        }
        
        overall_score = sum(improvement_metrics[key] * weight for key, weight in weights.items())
        improvement_metrics['overall_improvement_score'] = overall_score
        
        return {
            "improvement_scores": improvement_metrics,
            "detailed_analysis": {
                "failures": failure_analysis,
                "actions": action_analysis,
                "retries": retry_analysis,
                "costs": cost_analysis,
                "quality": quality_analysis,
                "timing": time_analysis
            }
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        return {
            "summary": {
                "total_logs": len(self.logs),
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "log_period": {
                    "start": min(log.get('timestamp', '') for log in self.logs) if self.logs else None,
                    "end": max(log.get('timestamp', '') for log in self.logs) if self.logs else None
                }
            },
            "improvement_metrics": self.calculate_improvement_metrics(),
            "recommendations": self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        failure_analysis = self.analyze_failure_patterns()
        quality_analysis = self.analyze_quality_metrics()
        cost_analysis = self.analyze_cost_metrics()
        retry_analysis = self.analyze_retry_patterns()
        
        # Failure-based recommendations
        failure_types = failure_analysis.get('failure_types', {})
        if failure_types.get('timeout', 0) > 5:
            recommendations.append("Consider increasing timeout limits or optimizing slow operations")
        
        if failure_types.get('api_error', 0) > 3:
            recommendations.append("Implement better error handling and API rate limiting")
        
        # Quality-based recommendations
        avg_improvement = quality_analysis.get('average_improvement', 0)
        if avg_improvement < 0.1:
            recommendations.append("Quality improvements are minimal, consider enhancing decision engine prompts")
        
        improvement_rate = quality_analysis.get('improvement_rate', 0)
        if improvement_rate < 0.5:
            recommendations.append("Less than 50% of evaluations show improvement, review quality thresholds")
        
        # Cost-based recommendations
        avg_cost = cost_analysis.get('average_cost_per_task', 0)
        if avg_cost > 0.05:
            recommendations.append("High average cost per task, consider model optimization")
        
        # Retry-based recommendations
        retry_success_rate = retry_analysis.get('retry_success_rate', 0)
        if retry_success_rate < 0.6:
            recommendations.append("Low retry success rate, improve retry strategies")
        
        if not recommendations:
            recommendations.append("System is performing well, continue monitoring")
        
        return recommendations
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """Export logs to pandas DataFrame for advanced analysis"""
        return pd.DataFrame(self.logs)
    
    def filter_logs(self, **filters) -> List[Dict[str, Any]]:
        """Filter logs based on criteria"""
        filtered_logs = self.logs
        
        for key, value in filters.items():
            filtered_logs = [log for log in filtered_logs if log.get(key) == value]
        
        return filtered_logs
    
    def get_time_series_data(self, metric: str, time_window: str = 'hour') -> Dict[str, List]:
        """Get time series data for specific metric"""
        time_series = defaultdict(list)
        
        for log in self.logs:
            timestamp = log.get('timestamp', '')
            if timestamp:
                # Parse timestamp and group by time window
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                if time_window == 'hour':
                    time_key = dt.strftime('%Y-%m-%d %H:00')
                elif time_window == 'day':
                    time_key = dt.strftime('%Y-%m-%d')
                else:  # minute
                    time_key = dt.strftime('%Y-%m-%d %H:%M')
                
                if metric in log:
                    time_series[time_key].append(log[metric])
        
        # Aggregate by time window
        aggregated_series = {}
        for time_key, values in time_series.items():
            if values:
                aggregated_series[time_key] = {
                    'count': len(values),
                    'sum': sum(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values)
                }
        
        return aggregated_series
