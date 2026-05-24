import { db } from '../firebase';
import { collection, addDoc, serverTimestamp, query, where, getDocs, orderBy, limit } from 'firebase/firestore';

// A small in-memory set to prevent double-logging in the same session (e.g. React Strict Mode)
const recentlyLogged = new Set();

/**
 * Logs a user action (e.g. Smart Recommendation, Image Diagnostic) to Firestore history.
 * @param {Object} user - The current logged in Firebase user 
 * @param {string} type - "Leaf Diagnostic" or "Smart Recommender"
 * @param {string} summary - A brief summary of the result/action
 * @param {Object} details - Full JSON response (optional)
 */
export const logUserAction = async (user, type, summary, details = {}) => {
  if (!user) return; // Do not log if not logged in
  
  // Deduplication key: prevent recording the same action twice within 10 seconds
  const dedupKey = `${user.uid}:${type}:${summary}`;
  if (recentlyLogged.has(dedupKey)) {
    console.log(`Skipping duplicate log for: ${type}`);
    return;
  }
  recentlyLogged.add(dedupKey);
  // Remove the key after 10 seconds to allow future identical actions to be logged
  setTimeout(() => recentlyLogged.delete(dedupKey), 10000);
  
  try {
    const historyRef = collection(db, 'history');
    await addDoc(historyRef, {
      userId: user.uid,
      userEmail: user.email,
      userName: user.displayName || 'Anonymous User',
      type: type,
      summary: summary,
      details: details,
      timestamp: serverTimestamp() // Firestore server time
    });
    console.log(`Successfully logged ${type} to history.`);
  } catch (error) {
    console.error("Error logging user history:", error);
  }
};
