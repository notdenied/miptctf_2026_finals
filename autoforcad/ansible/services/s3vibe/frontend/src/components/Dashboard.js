import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Dashboard.css';

const Dashboard = ({ user, token, onLogout }) => {
  const [buckets, setBuckets] = useState([]);
  const [selectedBucket, setSelectedBucket] = useState(null);
  const [objects, setObjects] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCreateBucket, setShowCreateBucket] = useState(false);
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [showDeleteBucket, setShowDeleteBucket] = useState(false);
  const [bucketToDelete, setBucketToDelete] = useState(null);
  const [newBucketName, setNewBucketName] = useState('');
  const [newFolderName, setNewFolderName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showBucketDropdown, setShowBucketDropdown] = useState(false);

  useEffect(() => {
    loadBuckets();
  }, []);

  useEffect(() => {
    if (selectedBucket) {
      localStorage.setItem('s3-bucket-id', selectedBucket.bucket_id);
      loadObjects();
    }
  }, [selectedBucket, currentPath]);

  const loadBuckets = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/buckets', {
        headers: {
          's3-auth-token': token
        }
      });
      const bucketsList = response.data.buckets || [];
      setBuckets(bucketsList);
      
      const savedBucketId = localStorage.getItem('s3-bucket-id');
      const savedBucket = bucketsList.find(b => b.bucket_id === savedBucketId);
      if (savedBucket) {
        setSelectedBucket(savedBucket);
      } else if (bucketsList.length > 0) {
        setSelectedBucket(bucketsList[0]);
      }
    } catch (err) {
      setError('Ошибка загрузки бакетов');
    } finally {
      setLoading(false);
    }
  };

  const createBucket = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const response = await axios.post('/api/buckets', {
        name: newBucketName
      }, {
        headers: {
          's3-auth-token': token
        }
      });

      if (response.data.success) {
        setSuccess('Бакет успешно создан!');
        setNewBucketName('');
        setShowCreateBucket(false);
        loadBuckets();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка создания бакета');
    }
  };

  const deleteBucket = async () => {
    if (!bucketToDelete) return;

    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await axios.delete(`/api/buckets/${bucketToDelete.bucket_id}`, {
        headers: {
          's3-auth-token': token
        }
      });

      setSuccess('Бакет успешно удален!');
      setShowDeleteBucket(false);
      setBucketToDelete(null);
      
      if (selectedBucket?.bucket_id === bucketToDelete.bucket_id) {
        setSelectedBucket(null);
        setCurrentPath('');
      }
      
      loadBuckets();
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка удаления бакета');
    } finally {
      setLoading(false);
    }
  };

  const loadObjects = async () => {
    if (!selectedBucket) return;

    setLoading(true);
    try {
      const prefix = currentPath ? `${currentPath}/` : '';
      const response = await axios.get(`/s3/objects?prefix=${prefix}`, {
        headers: {
          's3-auth-token': token,
          's3-bucket-id': selectedBucket.bucket_id,
          'Accept': 'application/json'
        }
      });
      
      let data = response.data;
      if (typeof data === 'string') {
        try {
          data = JSON.parse(data);
        } catch (e) {
          throw new Error('Не удалось разобрать ответ сервера');
        }
      }
      
      const allObjects = data.objects || [];
      
      const folders = [];
      const files = [];

      allObjects.forEach(obj => {
        if (obj.Key.endsWith('/')) {
          const folderKey = obj.Key.slice(0, -1);
          folders.push({
            name: folderKey.split('/').pop(),
            isFolder: true,
            path: folderKey,
            lastModified: obj.LastModified
          });
        } else {
          files.push({
            name: obj.Key.split('/').pop(),
            isFolder: false,
            size: obj.Size,
            lastModified: obj.LastModified,
            path: obj.Key
          });
        }
      });

      setObjects([...folders, ...files]);
    } catch (err) {
      setError('Ошибка загрузки объектов');
    } finally {
      setLoading(false);
    }
  };

  const createFolder = async (e) => {
    e.preventDefault();
    if (!selectedBucket || !newFolderName) return;

    const currentDepth = currentPath.split('/').filter(p => p).length;
    if (currentDepth >= 3) {
      setError('Максимальная глубина вложенности: 3 уровня');
      return;
    }

    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const folderPath = currentPath ? `${currentPath}/${newFolderName}` : newFolderName;
      
      await axios.put(
        `/s3/objects/${folderPath}/.keep`,
        '',
        {
          headers: {
            's3-auth-token': token,
            's3-bucket-id': selectedBucket.bucket_id,
            'Content-Type': 'text/plain'
          }
        }
      );

      setSuccess('Папка успешно создана!');
      setNewFolderName('');
      setShowCreateFolder(false);
      loadObjects();
    } catch (err) {
      setError('Ошибка создания папки');
    } finally {
      setLoading(false);
    }
  };

  const uploadObject = async (file) => {
    if (!file || !selectedBucket) return;

    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('Файл слишком большой. Максимальный размер: 5 МБ');
      return;
    }

    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const rawPath = currentPath ? `${currentPath}/${file.name}` : file.name;
      const encodedPath = rawPath
        .split('/')
        .map((seg) => encodeURIComponent(seg))
        .join('/');

      const contentType = file.type || 'application/octet-stream';

      const blob = new Blob([file], { type: contentType });

      await axios.put(
        `/s3/objects/${encodedPath}`,
        blob,
        {
          headers: {
            's3-auth-token': token,
            's3-bucket-id': selectedBucket.bucket_id,
            'Content-Type': contentType,
          },
          transformRequest: [(data) => data],
        }
      );

      setSuccess('Файл успешно загружен!');
      const fileInput = document.getElementById('fileInput');
      if (fileInput) fileInput.value = '';
      loadObjects();
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка загрузки файла');
    } finally {
      setLoading(false);
    }
  };

  const deleteObject = async (obj) => {
    if (!window.confirm(`Удалить ${obj.isFolder ? 'папку' : 'файл'} ${obj.name}?`)) return;

    setError('');
    setLoading(true);

    try {
      const deletePath = obj.isFolder ? `${obj.path}/.keep` : obj.path;
      await axios.delete(`/s3/objects/${deletePath}`, {
        headers: {
          's3-auth-token': token,
          's3-bucket-id': selectedBucket.bucket_id
        }
      });

      setSuccess('Удалено успешно!');
      loadObjects();
    } catch (err) {
      setError('Ошибка удаления');
    } finally {
      setLoading(false);
    }
  };

  const downloadObject = async (obj) => {
    try {
      const response = await axios.get(
        `/s3/objects/${obj.path}`,
        {
          headers: {
            's3-auth-token': token,
            's3-bucket-id': selectedBucket.bucket_id
          },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', obj.name);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError('Ошибка скачивания файла');
    }
  };

  const navigateToFolder = (folderName) => {
    const newPath = currentPath ? `${currentPath}/${folderName}` : folderName;
    setCurrentPath(newPath);
  };

  const navigateToPath = (index) => {
    const parts = currentPath.split('/').filter(p => p);
    if (index === -1) {
      setCurrentPath('');
    } else {
      setCurrentPath(parts.slice(0, index + 1).join('/'));
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const pathParts = currentPath.split('/').filter(p => p);

  return (
    <div className="dashboard-dark">
      <header className="header-dark">
        <div className="header-content-dark">
          <div className="header-left">
            <h1 className="header-title">Object Storage</h1>
            
            {buckets.length > 0 && (
              <div className="bucket-selector">
                <button 
                  className="bucket-dropdown-btn"
                  onClick={() => setShowBucketDropdown(!showBucketDropdown)}
                >
                  <span className="bucket-icon">🗄️</span>
                  <span className="bucket-name">{selectedBucket?.name || 'Выберите бакет'}</span>
                  <span className="dropdown-arrow">{showBucketDropdown ? '▲' : '▼'}</span>
                </button>
                
                {showBucketDropdown && (
                  <div className="bucket-dropdown-menu">
                    {buckets.map(bucket => (
                      <div
                        key={bucket.bucket_id}
                        className={`bucket-dropdown-item ${selectedBucket?.bucket_id === bucket.bucket_id ? 'active' : ''}`}
                      >
                        <div 
                          className="bucket-item-info"
                          onClick={() => {
                            setSelectedBucket(bucket);
                            setCurrentPath('');
                            setShowBucketDropdown(false);
                          }}
                        >
                          <div className="bucket-item-name">{bucket.name}</div>
                          <div className="bucket-item-size">{formatBytes(bucket.storage_used)}</div>
                        </div>
                        <button
                          className="bucket-delete-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setBucketToDelete(bucket);
                            setShowDeleteBucket(true);
                            setShowBucketDropdown(false);
                          }}
                          title="Удалить бакет"
                        >
                          🗑️
                        </button>
                      </div>
                    ))}
                    {buckets.length < 3 && (
                      <div className="bucket-dropdown-divider">
                        <button
                          className="bucket-create-btn"
                          onClick={() => {
                            setShowCreateBucket(true);
                            setShowBucketDropdown(false);
                          }}
                        >
                          + Создать бакет
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="header-right">
            <span className="user-name">{user?.username}</span>
            <button onClick={onLogout} className="btn-logout">Выход</button>
          </div>
        </div>
      </header>

      <div className="main-container-dark">
        {error && <div className="alert-error-dark">{error}</div>}
        {success && <div className="alert-success-dark">{success}</div>}

        {showCreateBucket && (
          <div className="modal-overlay" onClick={() => setShowCreateBucket(false)}>
            <div className="modal-dark" onClick={e => e.stopPropagation()}>
              <h2>Создать новый бакет</h2>
              <form onSubmit={createBucket}>
                <div className="form-group-dark">
                  <label>Имя бакета</label>
                  <input
                    type="text"
                    value={newBucketName}
                    onChange={(e) => setNewBucketName(e.target.value)}
                    placeholder="my-bucket"
                    required
                    minLength={3}
                  />
                </div>
                <div className="modal-actions">
                  <button type="button" onClick={() => setShowCreateBucket(false)} className="btn-secondary-dark">
                    Отмена
                  </button>
                  <button type="submit" className="btn-primary-dark">
                    Создать
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showCreateFolder && (
          <div className="modal-overlay" onClick={() => setShowCreateFolder(false)}>
            <div className="modal-dark" onClick={e => e.stopPropagation()}>
              <h2>Создать папку</h2>
              <form onSubmit={createFolder}>
                <div className="form-group-dark">
                  <label>Имя папки</label>
                  <input
                    type="text"
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    placeholder="folder-name"
                    required
                  />
                </div>
                <div className="modal-actions">
                  <button type="button" onClick={() => setShowCreateFolder(false)} className="btn-secondary-dark">
                    Отмена
                  </button>
                  <button type="submit" className="btn-primary-dark">
                    Создать
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showDeleteBucket && (
          <div className="modal-overlay" onClick={() => setShowDeleteBucket(false)}>
            <div className="modal-dark modal-danger" onClick={e => e.stopPropagation()}>
              <h2>Удалить бакет</h2>
              <p className="warning-text">
                Вы уверены, что хотите удалить бакет <strong>{bucketToDelete?.name}</strong>?
                Все содержимое бакета будет удалено без возможности восстановления.
              </p>
              <div className="modal-actions">
                <button 
                  type="button" 
                  onClick={() => {
                    setShowDeleteBucket(false);
                    setBucketToDelete(null);
                  }} 
                  className="btn-secondary-dark"
                >
                  Отмена
                </button>
                <button 
                  onClick={deleteBucket} 
                  className="btn-danger-dark"
                  disabled={loading}
                >
                  {loading ? 'Удаление...' : 'Удалить'}
                </button>
              </div>
            </div>
          </div>
        )}

        {!selectedBucket ? (
          <div className="empty-state">
            <h2>Выберите бакет для начала работы</h2>
            {buckets.length === 0 && (
              <button onClick={() => setShowCreateBucket(true)} className="btn-primary-dark">
                Создать первый бакет
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="path-navigation">
              <div className="breadcrumbs-compact">
                <div className="breadcrumb-item" onClick={() => navigateToPath(-1)}>
                  <span className="breadcrumb-icon">🏠</span>
                  <span className="breadcrumb-text">{selectedBucket.name}</span>
                </div>
                {pathParts.map((part, index) => (
                  <React.Fragment key={index}>
                    <span className="breadcrumb-sep">/</span>
                    <div 
                      className={`breadcrumb-item ${index === pathParts.length - 1 ? 'current' : ''}`}
                      onClick={() => navigateToPath(index)}
                    >
                      <span className="breadcrumb-text">{part}</span>
                    </div>
                  </React.Fragment>
                ))}
              </div>
            </div>

            <div className="toolbar">
              <div className="toolbar-left">
                <button 
                  onClick={() => setShowCreateFolder(true)} 
                  className="btn-toolbar"
                  disabled={pathParts.length >= 3}
                >
                  📁 Создать папку
                </button>
                <label className="btn-toolbar btn-upload">
                  📤 Загрузить файл
                  <input
                    id="fileInput"
                    type="file"
                    onChange={(e) => {
                      const file = e.target.files[0];
                      if (file) {
                        uploadObject(file);
                      }
                    }}
                    style={{ display: 'none' }}
                  />
                </label>
              </div>
              <div className="toolbar-right">
                <button onClick={loadObjects} className="btn-toolbar">
                  🔄 Обновить
                </button>
              </div>
            </div>

            <div className="file-list">
              {loading ? (
                <div className="loading-dark">
                  <div className="spinner-dark"></div>
                </div>
              ) : objects.length === 0 ? (
                <div className="empty-state">
                  <p>Папка пуста</p>
                </div>
              ) : (
                <table className="table-dark">
                  <thead>
                    <tr>
                      <th className="col-name">Имя</th>
                      <th className="col-size">Размер</th>
                      <th className="col-modified">Изменен</th>
                      <th className="col-actions">Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {objects.map((obj, index) => (
                      <tr key={index}>
                        <td className="col-name">
                          {obj.isFolder ? (
                            <div 
                              className="folder-item"
                              onClick={() => navigateToFolder(obj.name)}
                            >
                              <span className="icon-folder">📁</span>
                              <span>{obj.name}</span>
                            </div>
                          ) : (
                            <div className="file-item">
                              <span className="icon-file">📄</span>
                              <span>{obj.name}</span>
                            </div>
                          )}
                        </td>
                        <td className="col-size">
                          {obj.isFolder ? '—' : formatBytes(obj.size)}
                        </td>
                        <td className="col-modified">
                          {obj.isFolder ? '—' : new Date(obj.lastModified).toLocaleString('ru')}
                        </td>
                        <td className="col-actions">
                          {!obj.isFolder && (
                            <button 
                              onClick={() => downloadObject(obj)} 
                              className="btn-action"
                              title="Скачать"
                            >
                              ⬇️
                            </button>
                          )}
                          <button 
                            onClick={() => deleteObject(obj)} 
                            className="btn-action btn-delete"
                            title="Удалить"
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
