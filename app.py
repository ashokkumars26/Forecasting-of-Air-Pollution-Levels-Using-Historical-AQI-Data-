"""
Air Pollution Analysis and Forecasting System
Backend Flask Application

This application provides:
- Data loading and preprocessing
- AQI trend visualization
- Time-series forecasting using ARIMA
- Web interface for displaying results
"""

from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import warnings
warnings.filterwarnings('ignore')

# Try to import ARIMA, but use simple forecast if not available
try:
    from statsmodels.tsa.arima.model import ARIMA
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False
    print("Note: statsmodels not available. Using simple trend-based forecasting.")

app = Flask(__name__)

# Configuration
DATA_FILE = 'data/city_day.csv'  # Using Kaggle city_day.csv dataset
UPLOAD_FOLDER = 'data'

# Ensure data directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Cache for loaded dataset (to avoid reloading on every request)
_data_cache = None


def load_full_dataset(file_path):
    """
    Load the full city_day.csv dataset (with caching)
    Returns the complete dataset with all cities
    """
    global _data_cache
    
    # Return cached data if available
    if _data_cache is not None:
        return _data_cache
    
    try:
        # Load the dataset
        df = pd.read_csv(file_path)
        
        # Display column names for debugging
        print(f"Columns in dataset: {df.columns.tolist()}")
        
        # Identify date column (common variations for city_day.csv)
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        # If no date column found, assume first column is date
        if date_col is None:
            date_col = df.columns[0]
        
        # Convert date column to datetime
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Handle missing values in date column
        df = df.dropna(subset=[date_col])
        
        # Identify City column
        city_col = None
        for col in df.columns:
            if 'city' in col.lower():
                city_col = col
                break
        
        # Identify AQI column
        aqi_col = None
        for col in df.columns:
            if 'aqi' in col.lower() and 'bucket' not in col.lower():
                aqi_col = col
                break
        
        # If no AQI column found, look for numeric columns
        if aqi_col is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                aqi_col = numeric_cols[0]
        
        # Rename columns for easier handling
        rename_dict = {date_col: 'date', aqi_col: 'aqi'}
        if city_col:
            rename_dict[city_col] = 'city'
        
        df = df.rename(columns=rename_dict)
        
        # Ensure city column exists (if not, create a default)
        if 'city' not in df.columns:
            df['city'] = 'All Cities'
        
        # Ensure AQI values are numeric
        df['aqi'] = pd.to_numeric(df['aqi'], errors='coerce')
        
        # Remove rows with missing AQI
        df = df.dropna(subset=['aqi', 'date'])
        
        # Sort by date and city
        df = df.sort_values(['city', 'date'])
        
        # Reset index
        df = df.reset_index(drop=True)
        
        # Extract date components for grouping
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        
        # Cache the data
        _data_cache = df
        
        return df
    
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def load_and_preprocess_data(file_path, city=None):
    """
    Load CSV data and perform preprocessing for a specific city:
    - Handle missing values
    - Convert date column to datetime
    - Filter by city (if specified)
    - Sort by date
    - Remove duplicates
    """
    try:
        # Load full dataset (uses cache)
        df = load_full_dataset(file_path)
        
        if df is None:
            return None
        
        # Filter by city if specified
        if city and city != 'All Cities' and 'city' in df.columns:
            df = df[df['city'].str.strip().str.lower() == city.strip().lower()].copy()
            if len(df) == 0:
                print(f"No data found for city: {city}")
                return None
        
        # Handle missing values in AQI column (forward fill, then backward fill per city)
        if 'city' in df.columns:
            df['aqi'] = df.groupby('city')['aqi'].ffill().bfill()
        else:
            df['aqi'] = df['aqi'].ffill().bfill()
        
        # If still missing values, fill with mean
        df['aqi'] = df['aqi'].fillna(df['aqi'].mean())
        
        # Remove duplicates based on date (and city if applicable)
        if 'city' in df.columns:
            df = df.drop_duplicates(subset=['city', 'date'], keep='first')
        else:
            df = df.drop_duplicates(subset=['date'], keep='first')
        
        # Sort by date
        df = df.sort_values('date')
        
        # Reset index
        df = df.reset_index(drop=True)
        
        return df
    
    except Exception as e:
        print(f"Error preprocessing data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def calculate_daily_aqi(df):
    """Calculate daily average AQI"""
    daily_aqi = df.groupby(df['date'].dt.date)['aqi'].mean().reset_index()
    daily_aqi.columns = ['date', 'aqi']
    daily_aqi['date'] = pd.to_datetime(daily_aqi['date'])
    return daily_aqi


def calculate_monthly_aqi(df):
    """Calculate monthly average AQI"""
    # Extract year and month first
    df_copy = df.copy()
    df_copy['year'] = df_copy['date'].dt.year
    df_copy['month'] = df_copy['date'].dt.month
    
    # Group by year and month, then calculate mean AQI
    monthly_aqi = df_copy.groupby(['year', 'month'])['aqi'].mean().reset_index()
    
    # Create date column from year and month
    monthly_aqi['date'] = pd.to_datetime(monthly_aqi[['year', 'month']].assign(day=1))
    
    # Sort by date and return only date and aqi columns
    monthly_aqi = monthly_aqi[['date', 'aqi']].sort_values('date').reset_index(drop=True)
    return monthly_aqi


def forecast_aqi_simple(df, forecast_days=30):
    """
    Simple trend-based forecasting using moving average and linear trend
    This works without statsmodels/ARIMA
    
    Parameters:
    - df: DataFrame with 'date' and 'aqi' columns
    - forecast_days: Number of days to forecast
    
    Returns:
    - forecast: DataFrame with forecasted values
    """
    try:
        # Prepare time series data
        df_ts = df[['date', 'aqi']].copy()
        df_ts = df_ts.set_index('date')
        df_ts = df_ts.sort_index()
        
        # Resample to daily if needed
        if len(df_ts) > 0:
            df_ts = df_ts.resample('D').mean()
            df_ts = df_ts.ffill().bfill()
        
        if len(df_ts) < 7:
            raise ValueError("Not enough data for forecasting")
        
        # Calculate moving average (last 7 days)
        window = min(7, len(df_ts))
        recent_mean = df_ts['aqi'].tail(window).mean()
        recent_std = df_ts['aqi'].tail(window).std()
        
        # Calculate trend (linear regression on last 30 days)
        recent_data = df_ts['aqi'].tail(min(30, len(df_ts)))
        if len(recent_data) > 1:
            x = np.arange(len(recent_data))
            y = recent_data.values
            # Simple linear trend
            trend_slope = np.polyfit(x, y, 1)[0] if len(recent_data) > 1 else 0
        else:
            trend_slope = 0
        
        # Calculate seasonal component (if enough data)
        if len(df_ts) >= 365:
            # Use last year's pattern
            df_ts['day_of_year'] = df_ts.index.dayofyear
            seasonal_pattern = df_ts.groupby('day_of_year')['aqi'].mean()
        else:
            seasonal_pattern = None
        
        # Generate forecast
        last_date = df_ts.index[-1]
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=forecast_days, freq='D')
        
        forecast_values = []
        lower_bounds = []
        upper_bounds = []
        
        for i, forecast_date in enumerate(forecast_dates):
            # Base forecast: recent mean + trend
            base_forecast = recent_mean + (trend_slope * (i + 1))
            
            # Add seasonal adjustment if available
            if seasonal_pattern is not None:
                day_of_year = forecast_date.dayofyear
                if day_of_year in seasonal_pattern.index:
                    seasonal_adj = seasonal_pattern[day_of_year] - recent_mean
                    base_forecast += seasonal_adj * 0.3  # Weight seasonal component
            
            # Ensure forecast is within reasonable bounds
            base_forecast = max(0, min(500, base_forecast))
            
            # Calculate confidence intervals (95% confidence)
            confidence_range = recent_std * 1.96 if not pd.isna(recent_std) else recent_mean * 0.2
            
            forecast_values.append(base_forecast)
            lower_bounds.append(max(0, base_forecast - confidence_range))
            upper_bounds.append(min(500, base_forecast + confidence_range))
        
        # Create forecast DataFrame
        forecast_df = pd.DataFrame({
            'date': forecast_dates,
            'aqi': forecast_values,
            'lower_bound': lower_bounds,
            'upper_bound': upper_bounds
        })
        
        return forecast_df, None
        
    except Exception as e:
        print(f"Error in forecasting: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def forecast_aqi_arima(df, forecast_days=30):
    """
    Forecast future AQI values using ARIMA model (if available)
    Falls back to simple forecast if ARIMA is not available
    
    Parameters:
    - df: DataFrame with 'date' and 'aqi' columns
    - forecast_days: Number of days to forecast
    
    Returns:
    - forecast: DataFrame with forecasted values
    """
    # Use simple forecast if ARIMA is not available
    if not ARIMA_AVAILABLE:
        return forecast_aqi_simple(df, forecast_days)
    
    try:
        # Prepare time series data
        df_ts = df[['date', 'aqi']].copy()
        df_ts = df_ts.set_index('date')
        df_ts = df_ts.sort_index()
        
        # Resample to daily if needed (handle multiple readings per day)
        if len(df_ts) > 0:
            df_ts = df_ts.resample('D').mean()
            df_ts = df_ts.ffill().bfill()
        
        # Fit ARIMA model
        # Auto-select order if possible, otherwise use (1,1,1)
        try:
            # Try to find optimal parameters
            model = ARIMA(df_ts['aqi'], order=(1, 1, 1))
            fitted_model = model.fit()
        except:
            # Fallback to simpler model
            try:
                model = ARIMA(df_ts['aqi'], order=(1, 0, 1))
                fitted_model = model.fit()
            except:
                # Very simple model
                model = ARIMA(df_ts['aqi'], order=(1, 0, 0))
                fitted_model = model.fit()
        
        # Generate forecast
        forecast = fitted_model.forecast(steps=forecast_days)
        forecast_conf_int = fitted_model.get_forecast(steps=forecast_days).conf_int()
        
        # Create forecast dates
        last_date = df_ts.index[-1]
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=forecast_days, freq='D')
        
        # Create forecast DataFrame
        forecast_df = pd.DataFrame({
            'date': forecast_dates,
            'aqi': forecast.values,
            'lower_bound': forecast_conf_int.iloc[:, 0].values,
            'upper_bound': forecast_conf_int.iloc[:, 1].values
        })
        
        return forecast_df, fitted_model
        
    except Exception as e:
        print(f"Error in ARIMA forecasting: {str(e)}")
        print("Falling back to simple forecast method...")
        # Fallback to simple forecast
        return forecast_aqi_simple(df, forecast_days)


@app.route('/')
def index():
    """Main page route"""
    return render_template('index.html')


@app.route('/api/cities', methods=['GET'])
def get_cities():
    """API endpoint to get list of available cities"""
    try:
        df = load_full_dataset(DATA_FILE)
        if df is None:
            return jsonify({'error': 'Failed to load data'}), 500
        
        if 'city' in df.columns:
            cities = sorted(df['city'].unique().tolist())
            cities = [c for c in cities if pd.notna(c) and str(c).strip() != '']
        else:
            cities = ['All Cities']
        
        return jsonify({'cities': cities})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/load-data', methods=['POST'])
def load_data():
    """API endpoint to load and preprocess data"""
    try:
        # Check if data file exists
        if not os.path.exists(DATA_FILE):
            return jsonify({'error': f'Data file not found. Please ensure {DATA_FILE} exists in the data folder.'}), 404
        
        # Get city from request (optional)
        data = request.get_json() or {}
        city = data.get('city', None)
        
        # Load and preprocess data
        df = load_and_preprocess_data(DATA_FILE, city=city)
        
        if df is None or len(df) == 0:
            city_msg = f" for city '{city}'" if city else ""
            return jsonify({'error': f'Failed to load or preprocess data{city_msg}.'}), 500
        
        # Calculate statistics
        stats = {
            'total_records': len(df),
            'city': city if city else 'All Cities',
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d'),
                'end': df['date'].max().strftime('%Y-%m-%d')
            },
            'aqi_stats': {
                'mean': float(df['aqi'].mean()),
                'min': float(df['aqi'].min()),
                'max': float(df['aqi'].max()),
                'std': float(df['aqi'].std())
            }
        }
        
        city_msg = f" for {city}" if city else ""
        return jsonify({
            'success': True,
            'stats': stats,
            'message': f'Successfully loaded {len(df)} records{city_msg}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/daily-trend', methods=['GET'])
def daily_trend():
    """API endpoint to get daily AQI trend"""
    try:
        # Get city from query parameters
        city = request.args.get('city', None)
        
        df = load_and_preprocess_data(DATA_FILE, city=city)
        if df is None:
            return jsonify({'error': 'Failed to load data'}), 500
        
        daily_df = calculate_daily_aqi(df)
        
        # Convert to JSON format for frontend
        data = {
            'city': city if city else 'All Cities',
            'dates': daily_df['date'].dt.strftime('%Y-%m-%d').tolist(),
            'aqi_values': daily_df['aqi'].tolist()
        }
        
        return jsonify(data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/monthly-trend', methods=['GET'])
def monthly_trend():
    """API endpoint to get monthly AQI trend"""
    try:
        # Get city from query parameters
        city = request.args.get('city', None)
        
        df = load_and_preprocess_data(DATA_FILE, city=city)
        if df is None:
            return jsonify({'error': 'Failed to load data'}), 500
        
        monthly_df = calculate_monthly_aqi(df)
        
        # Convert to JSON format for frontend
        data = {
            'city': city if city else 'All Cities',
            'dates': monthly_df['date'].dt.strftime('%Y-%m-%d').tolist(),
            'aqi_values': monthly_df['aqi'].tolist()
        }
        
        return jsonify(data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/forecast', methods=['POST'])
def forecast():
    """API endpoint to generate AQI forecast"""
    try:
        # Get forecast days and city from request
        data = request.get_json() or {}
        forecast_days = data.get('days', 30)
        city = data.get('city', None)
        
        # Load and preprocess data
        df = load_and_preprocess_data(DATA_FILE, city=city)
        if df is None:
            return jsonify({'error': 'Failed to load data'}), 500
        
        # Calculate daily AQI for forecasting
        daily_df = calculate_daily_aqi(df)
        
        # Generate forecast
        forecast_df, model = forecast_aqi_arima(daily_df, forecast_days)
        
        if forecast_df is None:
            return jsonify({'error': 'Failed to generate forecast'}), 500
        
        # Get historical data for plotting
        historical_dates = daily_df['date'].dt.strftime('%Y-%m-%d').tolist()
        historical_aqi = daily_df['aqi'].tolist()
        
        # Prepare forecast data
        forecast_data = {
            'city': city if city else 'All Cities',
            'historical': {
                'dates': historical_dates,
                'aqi_values': historical_aqi
            },
            'forecast': {
                'dates': forecast_df['date'].dt.strftime('%Y-%m-%d').tolist(),
                'aqi_values': forecast_df['aqi'].tolist(),
                'lower_bound': forecast_df['lower_bound'].tolist(),
                'upper_bound': forecast_df['upper_bound'].tolist()
            }
        }
        
        return jsonify(forecast_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Run the Flask application
    print("Starting Air Pollution Analysis and Forecasting System...")
    print(f"Data file location: {DATA_FILE}")
    print("Using Kaggle city_day.csv dataset")
    print("Supported cities: Delhi, Chennai, Mumbai, and more...")
    app.run(debug=True, host='0.0.0.0', port=5000)

