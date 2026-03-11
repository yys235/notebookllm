import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Note, CreateNoteDto, UpdateNoteDto } from '@/types'
import { noteApi } from '@/api/notes'

export const useNoteStore = defineStore('note', () => {
  const notes = ref<Note[]>([])
  const currentNote = ref<Note | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchNotes() {
    loading.value = true
    error.value = null
    try {
      const response = await noteApi.getNotes()
      // Backend returns paginated response with items array
      // Response interceptor already unwraps the data
      if (response && typeof response === 'object') {
        // Handle paginated response: { items: [], total, page, page_size, total_pages }
        if ('items' in response) {
          notes.value = (response.items as Note[]) || []
        } else if (Array.isArray(response)) {
          notes.value = response as Note[]
        } else {
          notes.value = []
        }
      } else {
        notes.value = []
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch notes'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchNote(id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await noteApi.getNote(id)
      // Response interceptor already unwraps the data
      currentNote.value = response
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch note'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createNote(data: CreateNoteDto) {
    loading.value = true
    error.value = null
    try {
      const note = await noteApi.createNote(data)
      console.log('API response for createNote:', note)
      console.log('Note ID:', note?.id)
      notes.value.push(note)
      return note
    } catch (err: any) {
      error.value = err.message || 'Failed to create note'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateNote(id: string, data: UpdateNoteDto) {
    loading.value = true
    error.value = null
    try {
      const note = await noteApi.updateNote(id, data)
      const index = notes.value.findIndex((n: Note) => n.id === id)
      if (index !== -1) {
        notes.value[index] = note
      }
      if (currentNote.value?.id === id) {
        currentNote.value = note
      }
      return note
    } catch (err: any) {
      error.value = err.message || 'Failed to update note'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteNote(id: string) {
    loading.value = true
    error.value = null
    try {
      await noteApi.deleteNote(id)
      notes.value = notes.value.filter((n: Note) => n.id !== id)
      if (currentNote.value?.id === id) {
        currentNote.value = null
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to delete note'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    notes,
    currentNote,
    loading,
    error,
    fetchNotes,
    fetchNote,
    createNote,
    updateNote,
    deleteNote,
  }
})
